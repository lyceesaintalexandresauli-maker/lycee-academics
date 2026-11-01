"""Welfare intelligence analytics built entirely on real database records.

Never invents incidents or medical information. Every finding is sourced from
StudentWelfareRecord, DailyWelfareReport, and the student roster, and every
query is filtered by the authenticated user's role-based gender scope.
"""

from __future__ import annotations

import datetime
import re
from collections import defaultdict

from flask_login import current_user

from app.extensions import db
from app.models import User
from app.models.welfare import (
    LOCATION_STATUSES,
    URGENT_STATUSES,
    DailyWelfareReport,
    StudentWelfareRecord,
    WelfareAuditEvent,
)
from app.services.welfare_service import (
    CASE_LABELS,
    STATUS_LABELS,
    gender_values_for_role,
    scoped_students_for_role,
    student_in_scope,
)
from app.utils.helpers import get_setting, now_string


def _parse_date(value):
    if not value:
        return None
    try:
        return datetime.date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def repeated_concern_settings():
    try:
        min_count = int(get_setting("welfare_repeated_min_count", "2"))
    except (TypeError, ValueError):
        min_count = 2
    try:
        period_days = int(get_setting("welfare_repeated_period_days", "30"))
    except (TypeError, ValueError):
        period_days = 30
    return max(1, min_count), max(1, period_days)


def _scope_query(user=None):
    actor = user or current_user
    return scoped_students_for_role(actor.role)


def authorized_students(user=None):
    """Return students the current actor may see welfare data for."""
    return _scope_query(user).order_by(User.full_name).all()


def students_in_scope(student_ids, user=None):
    """Filter a list of student ids down to those in the actor's scope."""
    actor = user or current_user
    allowed = {s.id for s in _scope_query(actor)}
    return [sid for sid in student_ids if sid in allowed]


def welfare_records_for_student(student_id, user=None, limit=None):
    if not student_in_scope(db.session.get(User, student_id), user):
        return []
    query = StudentWelfareRecord.query.filter_by(student_id=student_id).order_by(
        StudentWelfareRecord.event_date.desc(), StudentWelfareRecord.id.desc()
    )
    if limit:
        query = query.limit(limit)
    return query.all()


def repeated_concerns(user=None, min_count=None, period_days=None):
    """Students with repeated welfare concerns within a configurable window.

    Returns a list of dicts ranked by follow-up priority, each backed by real
    records, dates, and evidence.
    """
    actor = user or current_user
    if actor.role not in {"patron", "matron", "master_admin", "head_teacher"}:
        return []
    if min_count is None or period_days is None:
        min_count, period_days = repeated_concern_settings()

    students = authorized_students(actor)
    student_ids = [s.id for s in students]
    if not student_ids:
        return []

    today = datetime.date.today()
    window_start = today - datetime.timedelta(days=period_days - 1)

    records = (
        StudentWelfareRecord.query.filter(
            StudentWelfareRecord.student_id.in_(student_ids),
            StudentWelfareRecord.event_date >= window_start.isoformat(),
            StudentWelfareRecord.event_date <= today.isoformat(),
        )
        .order_by(StudentWelfareRecord.student_id, StudentWelfareRecord.event_date.desc())
        .all()
    )

    by_student = defaultdict(list)
    for record in records:
        by_student[record.student_id].append(record)

    student_by_id = {s.id: s for s in students}
    results = []
    for student_id, recs in by_student.items():
        if len(recs) < min_count:
            continue
        student = student_by_id[student_id]
        latest = recs[0]
        unresolved = [r for r in recs if r.case_state != "resolved"]
        overdue_return = [
            r
            for r in recs
            if r.expected_return_date
            and _parse_date(r.expected_return_date)
            and _parse_date(r.expected_return_date) < today
            and not r.actual_return_date
            and r.status in {"sent_home", "authorized_leave"}
        ]
        urgent = any(r.is_urgent or r.status in URGENT_STATUSES for r in recs)
        follow_up_missing = any(not r.follow_up_required for r in unresolved)
        priority = "High" if (urgent or overdue_return or len(unresolved) >= 2) else "Medium"
        results.append(
            {
                "student": student,
                "record_count": len(recs),
                "period_days": period_days,
                "window_start": window_start.isoformat(),
                "latest_status": latest.status,
                "latest_status_label": STATUS_LABELS.get(latest.status, latest.status),
                "latest_date": latest.event_date,
                "latest_details": latest.details,
                "case_state": latest.case_state,
                "unresolved_count": len(unresolved),
                "overdue_return_count": len(overdue_return),
                "is_urgent": urgent,
                "priority": priority,
                "follow_up_missing": follow_up_missing,
                "evidence": [
                    {
                        "date": r.event_date,
                        "status": r.status,
                        "status_label": STATUS_LABELS.get(r.status, r.status),
                        "case_state": r.case_state,
                        "details": r.details,
                        "reporter_role": r.reporter_role,
                    }
                    for r in recs[:10]
                ],
            }
        )

    results.sort(
        key=lambda item: (
            {"High": 0, "Medium": 1, "Low": 2}.get(item["priority"], 1),
            -item["record_count"],
            item["student"].full_name or "",
        )
    )
    return results


def student_summary(student, user=None):
    """Full welfare profile for one authorized student."""
    actor = user or current_user
    if not student_in_scope(student, actor):
        return None
    records = welfare_records_for_student(student.id, actor)
    location_statuses = {"sick_at_school", "hospitalized", "sent_home", "authorized_leave"}
    active = None
    for record in records:
        if record.status in location_statuses and record.case_state != "resolved" and not record.actual_return_date:
            active = record
            break
    unresolved = [r for r in records if r.case_state != "resolved"]
    overdue_return = [
        r
        for r in records
        if r.expected_return_date
        and _parse_date(r.expected_return_date)
        and _parse_date(r.expected_return_date) < datetime.date.today()
        and not r.actual_return_date
        and r.status in {"sent_home", "authorized_leave"}
    ]
    sick_count = sum(1 for r in records if r.status == "sick_at_school")
    hospitalized_count = sum(1 for r in records if r.status == "hospitalized")
    home_count = sum(1 for r in records if r.status in {"sent_home", "authorized_leave"})
    return {
        "student": student,
        "total_reports": len(records),
        "sick_count": sick_count,
        "hospitalized_count": hospitalized_count,
        "home_count": home_count,
        "unresolved_count": len(unresolved),
        "active_welfare": active,
        "overdue_return": overdue_return,
        "records": [
            {
                "id": r.id,
                "date": r.event_date,
                "status": r.status,
                "status_label": STATUS_LABELS.get(r.status, r.status),
                "case_state": r.case_state,
                "case_state_label": CASE_LABELS.get(r.case_state, r.case_state),
                "details": r.details,
                "reported_by": r.reporter.full_name if r.reporter else "-",
                "reporter_role": r.reporter_role,
                "expected_return_date": r.expected_return_date,
                "actual_return_date": r.actual_return_date,
                "follow_up_required": r.follow_up_required,
                "follow_up_date": r.follow_up_date,
                "follow_up_notes": r.follow_up_notes,
                "notify_guardian": r.notify_guardian,
                "is_urgent": r.is_urgent,
                "requires_admin_approval": r.requires_admin_approval,
                "approval_status": r.approval_status,
                "resolved": r.case_state == "resolved",
            }
            for r in records
        ],
    }


def group_summary(student_ids, user=None):
    """Aggregate welfare picture for a trade/level/class selection."""
    actor = user or current_user
    allowed = students_in_scope(student_ids, actor)
    if not allowed:
        return {"students": [], "totals": {}}
    students = [db.session.get(User, sid) for sid in allowed]
    today = datetime.date.today()
    totals = {
        "enrolled": len(students),
        "with_concerns": 0,
        "repeated": 0,
        "hospitalized": 0,
        "sick_at_school": 0,
        "at_home": 0,
        "overdue_return": 0,
        "unresolved": 0,
        "needs_follow_up": 0,
    }
    repeated = repeated_concerns(actor)
    repeated_ids = {item["student"].id for item in repeated}
    student_rows = []
    for student in students:
        summary = student_summary(student, actor)
        if not summary:
            continue
        has_concern = summary["total_reports"] > 0
        if has_concern:
            totals["with_concerns"] += 1
        if student.id in repeated_ids:
            totals["repeated"] += 1
        active = summary["active_welfare"]
        if active:
            if active.status == "hospitalized":
                totals["hospitalized"] += 1
            elif active.status == "sick_at_school":
                totals["sick_at_school"] += 1
            elif active.status in {"sent_home", "authorized_leave"}:
                totals["at_home"] += 1
        if summary["overdue_return"]:
            totals["overdue_return"] += 1
        if summary["unresolved_count"]:
            totals["unresolved"] += 1
        if any(r["follow_up_required"] and not r["resolved"] for r in summary["records"]):
            totals["needs_follow_up"] += 1
        student_rows.append(
            {
                "student": student,
                "total_reports": summary["total_reports"],
                "unresolved": summary["unresolved_count"],
                "active_status": active.status if active else None,
                "active_label": STATUS_LABELS.get(active.status, active.status) if active else None,
                "repeated": student.id in repeated_ids,
                "overdue_return": bool(summary["overdue_return"]),
            }
        )
    student_rows.sort(key=lambda row: (row["total_reports"], row["student"].full_name or ""), reverse=True)
    return {"students": student_rows, "totals": totals}


_REPEATED_TRIGGERS = [
    (re.compile(r"repeated.*sick|sick.*repeated", re.I), "repeated sickness"),
    (re.compile(r"repeated.*hospital|hospital.*repeated", re.I), "repeated hospitalization"),
    (re.compile(r"repeated.*home|home.*repeated|sent home.*repeated", re.I), "repeated home absence"),
    (re.compile(r"repeated.*concern|concern.*repeated", re.I), "repeated concerns"),
    (re.compile(r"overdue|return date.*passed|past due", re.I), "overdue return dates"),
    (re.compile(r"unresolved", re.I), "unresolved cases"),
    (re.compile(r"follow.?up", re.I), "follow-up"),
    (re.compile(r"urgent|immediate|priority", re.I), "urgent cases"),
]


def answer_ai_question(question, user=None):
    """Rule-based welfare intelligence answer backed by real records.

    Enforces the same role/gender permissions as ordinary dashboard requests.
    Never invents incidents or medical information.
    """
    actor = user or current_user
    if actor.role not in {"patron", "matron", "master_admin", "head_teacher"}:
        return {
            "answer": "You are not authorized to use the welfare intelligence assistant.",
            "scope": actor.role,
            "students": [],
            "evidence": [],
        }

    q = (question or "").strip()
    if not q:
        return {
            "answer": "Please ask a welfare question, for example: 'Which assigned students have repeated welfare concerns?'",
            "scope": actor.role,
            "students": [],
            "evidence": [],
        }

    repeated = repeated_concerns(actor)
    students = authorized_students(actor)

    def student_rows(items):
        rows = []
        for item in items:
            s = item["student"]
            rows.append(
                {
                    "student": s.full_name,
                    "registration_number": s.sdms_code or "-",
                    "class": s.class_name or "-",
                    "trade": s.trade or "-",
                    "level": s.level or "-",
                    "latest_status": item["latest_status_label"],
                    "priority": item["priority"],
                    "record_count": item["record_count"],
                    "unresolved": item["unresolved_count"],
                    "overdue_return": item["overdue_return_count"],
                    "latest_date": item["latest_date"],
                }
            )
        return rows

    lower = q.lower()
    matched = None
    for pattern, label in _REPEATED_TRIGGERS:
        if pattern.search(lower):
            matched = label
            break

    if matched in {"repeated sickness", "repeated hospitalization", "repeated home absence", "repeated concerns"} or (
        "repeated" in lower and "concern" in lower
    ):
        items = repeated
        if matched == "repeated sickness":
            items = [i for i in repeated if any(e["status"] == "sick_at_school" for e in i["evidence"])]
        elif matched == "repeated hospitalization":
            items = [i for i in repeated if any(e["status"] == "hospitalized" for e in i["evidence"])]
        elif matched == "repeated home absence":
            items = [i for i in repeated if any(e["status"] in {"sent_home", "authorized_leave"} for e in i["evidence"])]
        answer = (
            f"Based on welfare records from the last {repeated[0]['period_days'] if repeated else 30} days, "
            f"{len(items)} assigned student(s) show repeated welfare concerns meeting the configured threshold."
            if items
            else "No assigned students currently meet the repeated-concern threshold in the configured window."
        )
        return {
            "answer": answer,
            "scope": actor.role,
            "students": student_rows(items),
            "evidence": [e for i in items for e in i["evidence"]][:20],
        }

    if "overdue" in lower or "return date" in lower:
        items = [i for i in repeated if i["overdue_return_count"]]
        answer = (
            f"{len(items)} assigned student(s) have an expected return date that has passed without a recorded return."
            if items
            else "No assigned students have overdue expected return dates."
        )
        return {
            "answer": answer,
            "scope": actor.role,
            "students": student_rows(items),
            "evidence": [],
        }

    if "unresolved" in lower:
        items = [i for i in repeated if i["unresolved_count"]]
        answer = (
            f"{len(items)} assigned student(s) have at least one unresolved welfare case."
            if items
            else "No assigned students have unresolved welfare cases."
        )
        return {
            "answer": answer,
            "scope": actor.role,
            "students": student_rows(items),
            "evidence": [],
        }

    if "follow.?up" in lower or "follow up" in lower:
        items = [i for i in repeated if i["follow_up_missing"] or i["priority"] == "High"]
        answer = (
            f"{len(items)} assigned student(s) require follow-up attention based on current welfare records."
            if items
            else "No assigned students currently require recorded follow-up."
        )
        return {
            "answer": answer,
            "scope": actor.role,
            "students": student_rows(items),
            "evidence": [],
        }

    if "urgent" in lower or "immediate" in lower:
        items = [i for i in repeated if i["is_urgent"]]
        answer = (
            f"{len(items)} assigned student(s) have an urgent welfare indicator (hospitalization or emergency)."
            if items
            else "No assigned students currently have an urgent welfare indicator."
        )
        return {
            "answer": answer,
            "scope": actor.role,
            "students": student_rows(items),
            "evidence": [e for i in items for e in i["evidence"]][:20],
        }

    if "history" in lower:
        answer = (
            "Open an individual student's welfare profile to view their complete welfare history, "
            "including report dates, statuses, case states, and follow-up notes."
        )
        return {"answer": answer, "scope": actor.role, "students": [], "evidence": []}

    # Default: surface repeated concerns as the primary intelligence answer.
    items = repeated
    answer = (
        f"{len(items)} assigned student(s) currently have repeated or high-priority welfare concerns."
        if items
        else "No assigned students currently have repeated or high-priority welfare concerns."
    )
    return {
        "answer": answer,
        "scope": actor.role,
        "students": student_rows(items[:10]),
        "evidence": [e for i in items[:5] for e in i["evidence"]][:20],
    }
