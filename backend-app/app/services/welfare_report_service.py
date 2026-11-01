"""Daily consolidated welfare report generation and delivery to the Admin."""

from __future__ import annotations

import datetime

from flask_login import current_user

from app.extensions import db
from app.models import User
from app.models.welfare import DailyWelfareReport, StudentWelfareRecord, WelfareAuditEvent
from app.services.welfare_analytics_service import authorized_students, repeated_concerns
from app.services.welfare_service import (
    CARE_ROLES,
    LEADER_ROLES,
    scoped_students_for_role,
    snapshot_totals,
)
from app.utils.helpers import get_setting, now_string
from app.utils.notifications import notify_users


def _parse_date(value):
    if not value:
        return None
    try:
        return datetime.date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def deadline_settings():
    try:
        hour = int(get_setting("welfare_daily_report_hour", "8"))
    except (TypeError, ValueError):
        hour = 8
    try:
        minute = int(get_setting("welfare_daily_report_minute", "0"))
    except (TypeError, ValueError):
        minute = 0
    return max(0, min(23, hour)), max(0, min(59, minute))


def _role_label(role):
    return "Patron (Boys)" if role == "patron" else "Matron (Girls)"


def consolidated_report_for_day(report_date=None, user=None):
    """Build the consolidated boys + girls welfare picture for one calendar date.

    Only authorized students are included; a Patron never sees girls, a Matron
    never sees boys, and an Admin sees both.
    """
    actor = user or current_user
    report_date = report_date or datetime.date.today().isoformat()
    day = _parse_date(report_date) or datetime.date.today()

    patron_students = scoped_students_for_role("patron").all()
    matron_students = scoped_students_for_role("matron").all()

    def totals_for(role, students):
        student_ids = [s.id for s in students]
        records = StudentWelfareRecord.query.filter(
            StudentWelfareRecord.student_id.in_(student_ids),
            StudentWelfareRecord.event_date == report_date,
        ).all() if student_ids else []
        open_records = StudentWelfareRecord.query.filter(
            StudentWelfareRecord.student_id.in_(student_ids),
            StudentWelfareRecord.case_state != "resolved",
        ).all() if student_ids else []
        return {
            "role": role,
            "role_label": _role_label(role),
            "total_students": len(students),
            "sick_count": sum(1 for r in records if r.status == "sick_at_school"),
            "hospitalized_count": sum(1 for r in records if r.status == "hospitalized"),
            "at_home_count": sum(1 for r in records if r.status in {"sent_home", "authorized_leave"}),
            "follow_up_count": sum(
                1 for r in open_records if r.follow_up_required or r.case_state == "follow_up"
            ),
            "urgent_count": sum(1 for r in records if r.is_urgent or r.status in {"hospitalized", "emergency"}),
            "submitted": DailyWelfareReport.query.filter_by(
                reporter_role=role, report_date=report_date
            ).first() is not None,
        }

    patron_totals = totals_for("patron", patron_students)
    matron_totals = totals_for("matron", matron_students)

    repeated = repeated_concerns(actor)
    repeated_count = len(repeated)
    repeated_students = [item["student"].full_name for item in repeated]

    overdue_return = []
    unresolved = []
    urgent = []
    for item in repeated:
        s = item["student"]
        if item["overdue_return_count"]:
            overdue_return.append(s.full_name)
        if item["unresolved_count"]:
            unresolved.append(s.full_name)
        if item["is_urgent"]:
            urgent.append(s.full_name)

    missing = []
    late = []
    for role in ("patron", "matron"):
        has_active = User.query.filter_by(role=role, is_active_account=True).first()
        if not has_active:
            continue
        submitted = DailyWelfareReport.query.filter_by(reporter_role=role, report_date=report_date).first()
        if not submitted:
            missing.append(role)
        else:
            submitted_time = _parse_date(submitted.submitted_at) or day
            deadline_dt = datetime.datetime.combine(day, datetime.time(*deadline_settings()))
            if submitted_time > deadline_dt:
                late.append(role)

    consolidated = {
        "report_date": report_date,
        "generated_at": now_string(),
        "patron": patron_totals,
        "matron": matron_totals,
        "total_boys_concerns": patron_totals["sick_count"] + patron_totals["hospitalized_count"] + patron_totals["at_home_count"],
        "total_girls_concerns": matron_totals["sick_count"] + matron_totals["hospitalized_count"] + matron_totals["at_home_count"],
        "repeated_count": repeated_count,
        "repeated_students": repeated_students,
        "hospitalized_students": urgent,  # urgent covers hospitalized/emergency
        "sick_students": [item["student"].full_name for item in repeated if any(e["status"] == "sick_at_school" for e in item["evidence"])],
        "home_students": [item["student"].full_name for item in repeated if any(e["status"] in {"sent_home", "authorized_leave"} for e in item["evidence"])],
        "overdue_return_students": overdue_return,
        "unresolved_students": unresolved,
        "urgent_students": urgent,
        "missing_submissions": missing,
        "late_submissions": late,
        "deadline_hour": deadline_settings()[0],
        "deadline_minute": deadline_settings()[1],
    }
    return consolidated


def report_history(limit=30, user=None):
    actor = user or current_user
    if actor.role not in LEADER_ROLES:
        return []
    reports = (
        DailyWelfareReport.query.order_by(DailyWelfareReport.report_date.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": r.id,
            "report_date": r.report_date,
            "reporter_role": r.reporter_role,
            "reporter_name": r.reporter.full_name if r.reporter else "-",
            "submitted_at": r.submitted_at,
            "total_students": r.total_students,
            "sick_count": r.sick_count,
            "hospitalized_count": r.hospitalized_count,
            "sent_home_count": r.sent_home_count,
            "follow_up_count": r.follow_up_count,
            "incident_count": r.incident_count,
            "reviewed": r.reviewed_by_id is not None,
            "observations": r.observations,
            "recommended_actions": r.recommended_actions,
        }
        for r in reports
    ]


def delivery_log(limit=50):
    return (
        WelfareAuditEvent.query.filter(
            WelfareAuditEvent.action.in_(("daily_report_generated", "daily_report_delivered", "daily_report_failed"))
        )
        .order_by(WelfareAuditEvent.created_at.desc())
        .limit(limit)
        .all()
    )


def log_delivery(actor, report_date, action, reason, report=None):
    from app.services.welfare_service import write_audit

    db.session.add(
        WelfareAuditEvent(
            actor_id=actor.id,
            actor_name=actor.full_name,
            action=action,
            report_id=report.id if report else None,
            before_state=None,
            after_state=action,
            reason=reason,
            created_at=now_string(),
        )
    )
    db.session.commit()


def send_consolidated_report(actor=None, report_date=None):
    """Generate and deliver the consolidated daily welfare report to school admins.

    Returns (success, message). Records delivery success/failure in the audit log.
    """
    actor = actor or current_user
    report_date = report_date or datetime.date.today().isoformat()
    data = consolidated_report_for_day(report_date, actor)

    recipients = [
        u.id
        for u in User.query.filter(
            User.role.in_(LEADER_ROLES), User.is_active_account.is_(True)
        ).all()
    ]

    title = f"Daily Welfare Report - {report_date}"
    body_lines = [
        f"Consolidated welfare report for {report_date} (generated {data['generated_at']}).",
        f"Boys with welfare concerns: {data['total_boys_concerns']} (Patron).",
        f"Girls with welfare concerns: {data['total_girls_concerns']} (Matron).",
        f"Students with repeated concerns: {data['repeated_count']}.",
        f"Hospitalized/urgent: {len(data['urgent_students'])}.",
        f"Sick at school: {len(data['sick_students'])}.",
        f"Staying at home: {len(data['home_students'])}.",
        f"Overdue return dates: {len(data['overdue_return_students'])}.",
        f"Unresolved cases: {len(data['unresolved_students'])}.",
    ]
    if data["missing_submissions"]:
        body_lines.append(
            "Missing submissions: " + ", ".join(_role_label(r) for r in data["missing_submissions"])
        )
    if data["late_submissions"]:
        body_lines.append(
            "Late submissions: " + ", ".join(_role_label(r) for r in data["late_submissions"])
        )
    body = "\n".join(body_lines)

    try:
        notify_users(recipients, "Welfare", title, body, "/welfare/admin")
        log_delivery(actor, report_date, "daily_report_delivered", "Consolidated daily welfare report delivered to administrators.")
        return True, "Consolidated welfare report delivered to administrators."
    except Exception as exc:  # pragma: no cover - delivery path defensive
        log_delivery(actor, report_date, "daily_report_failed", f"Delivery failed: {exc}")
        return False, f"Failed to deliver consolidated report: {exc}"
