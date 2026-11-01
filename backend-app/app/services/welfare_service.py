import datetime

from flask_login import current_user

from app.extensions import db
from app.models import Attendance, User
from app.models.welfare import (
    APPROVAL_STATUSES,
    LOCATION_STATUSES,
    URGENT_STATUSES,
    DailyWelfareReport,
    StudentWelfareRecord,
    WelfareAuditEvent,
)
from app.utils.helpers import now_string
from app.utils.notifications import notify_school_admins, notify_student_and_parent, notify_users


STATUS_LABELS = {
    "sick_at_school": "Sick at school",
    "hospitalized": "Hospitalized",
    "sent_home": "Sent home with authorization",
    "authorized_leave": "Authorized leave",
    "welfare_concern": "Welfare concern",
    "emergency": "Emergency",
    "misconduct_report": "Misconduct report",
}

CASE_LABELS = {
    "open": "Open",
    "follow_up": "Follow-up",
    "awaiting_info": "Awaiting information",
    "awaiting_approval": "Awaiting approval",
    "resolved": "Resolved",
}

OFFICIAL_PRESENT = "Present"
OFFICIAL_PRESENT_SICK = "Present but sick at school"
OFFICIAL_HOSPITALIZED = "Hospitalized"
OFFICIAL_HOME = "At home with authorization"
OFFICIAL_UNACCOUNTED = "Unaccounted"

CARE_ROLES = {"patron", "matron"}
LEADER_ROLES = {"master_admin", "head_teacher"}
MALE_VALUES = {"male", "m", "boy"}
FEMALE_VALUES = {"female", "f", "girl"}


def gender_values_for_role(role):
    if role == "patron":
        return MALE_VALUES
    if role == "matron":
        return FEMALE_VALUES
    return set()


def scoped_students_for_role(role):
    query = User.query.filter_by(role="student")
    if role in LEADER_ROLES:
        return query
    genders = gender_values_for_role(role)
    if not genders:
        return query.filter(db.false())
    return query.filter(db.func.lower(User.gender).in_(genders))


def scoped_students(user=None):
    actor = user or current_user
    return scoped_students_for_role(actor.role)


def student_in_scope(student, user=None):
    if not student or student.role != "student":
        return False
    actor = user or current_user
    if actor.role in LEADER_ROLES:
        return True
    genders = gender_values_for_role(actor.role)
    return bool(genders) and (student.gender or "").strip().casefold() in genders


def active_location_record(student_id):
    return StudentWelfareRecord.query.filter(
        StudentWelfareRecord.student_id == student_id,
        StudentWelfareRecord.status.in_(LOCATION_STATUSES),
        StudentWelfareRecord.case_state != "resolved",
        StudentWelfareRecord.actual_return_date.is_(None),
    ).order_by(StudentWelfareRecord.id.desc()).first()


def active_welfare_for_day(student_id, day):
    records = StudentWelfareRecord.query.filter(
        StudentWelfareRecord.student_id == student_id,
        StudentWelfareRecord.event_date <= day,
        StudentWelfareRecord.status.in_(LOCATION_STATUSES),
    ).order_by(StudentWelfareRecord.id.desc()).all()
    for record in records:
        ended = record.actual_return_date or ""
        if ended and ended < day:
            continue
        if record.expected_return_date and record.expected_return_date < day and not record.actual_return_date:
            if record.status in {"sent_home", "authorized_leave"}:
                return record
        return record
    return None


def rfid_status_for(student_id, day):
    record = Attendance.query.filter_by(student_id=student_id, day=day).order_by(Attendance.id.desc()).first()
    return record.status if record else None, record


def official_attendance_label(rfid_status, welfare_status=None):
    """Combine RFID physical presence with approved welfare without mutating RFID."""
    if welfare_status == "hospitalized":
        return OFFICIAL_HOSPITALIZED
    if welfare_status in {"sent_home", "authorized_leave"}:
        return OFFICIAL_HOME
    if welfare_status == "sick_at_school":
        if (rfid_status or "").strip() in {"Present", "Late"}:
            return OFFICIAL_PRESENT_SICK
        return OFFICIAL_PRESENT_SICK
    physical = (rfid_status or "").strip()
    if physical in {"Present", "Late"}:
        return OFFICIAL_PRESENT if physical == "Present" else physical
    return OFFICIAL_UNACCOUNTED


def official_attendance_for_student(student_id, day):
    rfid_status, attendance = rfid_status_for(student_id, day)
    welfare = active_welfare_for_day(student_id, day)
    welfare_status = welfare.status if welfare else None
    return {
        "rfid_status": rfid_status or "Not marked",
        "welfare_status": welfare_status,
        "official_status": official_attendance_label(rfid_status, welfare_status),
        "attendance": attendance,
        "welfare": welfare,
    }


def write_audit(action, *, student=None, record=None, report=None, before=None, after=None, reason=None):
    db.session.add(WelfareAuditEvent(
        actor_id=current_user.id,
        actor_name=current_user.full_name,
        action=action,
        student_id=student.id if student else (record.student_id if record else None),
        record_id=record.id if record else None,
        report_id=report.id if report else None,
        before_state=before,
        after_state=after,
        reason=reason,
        created_at=now_string(),
    ))


def _admin_ids():
    return [user.id for user in User.query.filter(User.role.in_(LEADER_ROLES)).all()]


def notify_welfare_event(record, title, body):
    notify_school_admins("Welfare", title, body, "/welfare")
    if record.notify_guardian and record.student:
        notify_student_and_parent(record.student, "Welfare", title, body, "/welfare")


def snapshot_totals(role, day):
    students = scoped_students_for_role(role).all()
    student_ids = [student.id for student in students]
    records = StudentWelfareRecord.query.filter(
        StudentWelfareRecord.event_date == day,
        StudentWelfareRecord.reporter_role == role,
    ).all() if student_ids else []
    open_records = StudentWelfareRecord.query.filter(
        StudentWelfareRecord.reporter_role == role,
        StudentWelfareRecord.case_state != "resolved",
    ).all()
    return {
        "total_students": len(students),
        "sick_count": sum(1 for item in records if item.status == "sick_at_school"),
        "hospitalized_count": sum(1 for item in records if item.status == "hospitalized"),
        "sent_home_count": sum(1 for item in records if item.status in {"sent_home", "authorized_leave"}),
        "follow_up_count": sum(1 for item in open_records if item.follow_up_required or item.case_state == "follow_up"),
        "incident_count": sum(1 for item in records if item.status in URGENT_STATUSES or item.is_urgent),
    }


def create_welfare_record(actor, student, payload):
    if actor.role not in CARE_ROLES:
        raise PermissionError("Only the Patron or Matron can create welfare records.")
    if not student_in_scope(student, actor):
        raise PermissionError("This student is outside your authorized welfare scope.")
    status = payload["status"]
    details = payload["details"]
    event_date = payload["event_date"]
    if status in LOCATION_STATUSES and active_location_record(student.id):
        raise ValueError("Resolve the student's current sickness, hospital, or leave record before opening another.")
    if status == "authorized_leave" and not payload.get("authorization_by"):
        raise ValueError("Authorized leave requires a named approver.")
    if status in {"sent_home", "authorized_leave"} and not payload.get("expected_return_date"):
        raise ValueError("Enter an expected return date for students sent home or on authorized leave.")
    needs_approval = status in APPROVAL_STATUSES or payload.get("requires_admin_approval")
    timestamp = now_string()
    record = StudentWelfareRecord(
        student_id=student.id,
        student_name=student.full_name,
        class_name=student.class_name,
        gender=student.gender,
        reporter_id=actor.id,
        reporter_role=actor.role,
        status=status,
        case_state="awaiting_approval" if needs_approval else ("follow_up" if payload.get("follow_up_required") else "open"),
        details=details,
        authorization_by=payload.get("authorization_by") or None,
        authorization_note=payload.get("authorization_note") or None,
        event_date=event_date,
        expected_return_date=payload.get("expected_return_date") or None,
        follow_up_required=bool(payload.get("follow_up_required")),
        follow_up_date=payload.get("follow_up_date") or None,
        follow_up_notes=payload.get("follow_up_notes") or None,
        notify_guardian=bool(payload.get("notify_guardian")),
        is_urgent=status in URGENT_STATUSES or bool(payload.get("is_urgent")),
        requires_admin_approval=bool(needs_approval),
        approval_status="pending" if needs_approval else "not_required",
        created_at=timestamp,
        updated_at=timestamp,
    )
    db.session.add(record)
    db.session.flush()
    write_audit("Welfare record created", student=student, record=record, after=record.case_state, reason=details)
    title = f"{STATUS_LABELS[status]}: {student.full_name}"
    body = details
    if status in {"hospitalized", "sent_home", "emergency", "authorized_leave"} or record.is_urgent:
        notify_welfare_event(record, title, body)
    else:
        notify_school_admins("Welfare", title, body, "/welfare")
        if record.notify_guardian:
            notify_student_and_parent(student, "Welfare", title, body, "/welfare")
    return record


def record_return(actor, record, return_date, note):
    if actor.role not in CARE_ROLES | LEADER_ROLES:
        raise PermissionError("You cannot record a return for this case.")
    if actor.role in CARE_ROLES and record.reporter_role != actor.role:
        raise PermissionError("You can only update cases in your welfare scope.")
    if record.case_state == "resolved" and record.actual_return_date:
        raise ValueError("This welfare record is already closed.")
    before = record.case_state
    record.actual_return_date = return_date
    record.resolution_note = note
    record.resolved_by_id = actor.id
    record.resolved_at = now_string()
    record.case_state = "resolved"
    record.updated_at = now_string()
    write_audit("Welfare return recorded", record=record, student=record.student, before=before, after="resolved", reason=note)
    return record


def add_follow_up(actor, record, note, follow_up_date=None):
    if actor.role not in CARE_ROLES | LEADER_ROLES:
        raise PermissionError("You cannot add follow-up notes.")
    if actor.role in CARE_ROLES and not student_in_scope(record.student, actor):
        raise PermissionError("This student is outside your authorized welfare scope.")
    before = record.case_state
    record.follow_up_required = True
    record.follow_up_notes = "\n".join(part for part in (record.follow_up_notes, note) if part)
    if follow_up_date:
        record.follow_up_date = follow_up_date
    if record.case_state not in {"awaiting_approval", "resolved"}:
        record.case_state = "follow_up"
    record.updated_at = now_string()
    write_audit("Welfare follow-up recorded", record=record, student=record.student, before=before, after=record.case_state, reason=note)
    return record


def submit_daily_report(actor, report_date, observations, recommended_actions, serious_incidents):
    if actor.role not in CARE_ROLES:
        raise PermissionError("Only the Patron or Matron can submit a daily welfare report.")
    existing = DailyWelfareReport.query.filter_by(reporter_role=actor.role, report_date=report_date).first()
    if existing:
        raise ValueError("A daily welfare report for this date has already been submitted.")
    totals = snapshot_totals(actor.role, report_date)
    report = DailyWelfareReport(
        reporter_role=actor.role,
        reporter_id=actor.id,
        report_date=report_date,
        observations=observations,
        recommended_actions=recommended_actions or None,
        serious_incidents=serious_incidents or None,
        submitted_at=now_string(),
        **totals,
    )
    db.session.add(report)
    db.session.flush()
    write_audit("Daily welfare report submitted", report=report, after="submitted", reason=observations)
    notify_school_admins(
        "Welfare",
        f"{actor.role.replace('_', ' ').title()} daily report submitted",
        f"{actor.full_name} submitted the {report_date} welfare report.",
        "/welfare",
    )
    return report


def review_daily_report(actor, report, comments):
    if actor.role not in LEADER_ROLES:
        raise PermissionError("Only school leadership can review welfare reports.")
    report.reviewed_by_id = actor.id
    report.reviewed_at = now_string()
    report.review_comments = comments or None
    write_audit("Daily welfare report reviewed", report=report, after="reviewed", reason=comments)
    if report.reporter_id:
        notify_users([report.reporter_id], "Welfare", "Daily welfare report reviewed", comments or "Leadership reviewed your report.", "/welfare")
    return report


def request_more_information(actor, record, question):
    if actor.role not in LEADER_ROLES:
        raise PermissionError("Only school leadership can request additional welfare information.")
    before = record.case_state
    record.info_request = question
    record.case_state = "awaiting_info"
    record.reviewed_by_id = actor.id
    record.reviewed_at = now_string()
    record.updated_at = now_string()
    write_audit("Additional information requested", record=record, student=record.student, before=before, after="awaiting_info", reason=question)
    notify_users([record.reporter_id], "Welfare", f"Information requested: {record.student_name}", question, "/welfare")
    return record


def respond_to_information_request(actor, record, response):
    if actor.role not in CARE_ROLES or record.reporter_role != actor.role:
        raise PermissionError("You can only answer information requests for your welfare cases.")
    before = record.case_state
    record.info_response = response
    record.case_state = "awaiting_approval" if record.requires_admin_approval and record.approval_status == "pending" else "follow_up"
    record.updated_at = now_string()
    write_audit("Information request answered", record=record, student=record.student, before=before, after=record.case_state, reason=response)
    notify_school_admins("Welfare", f"Information received: {record.student_name}", response, "/welfare")
    return record


def assign_follow_up(actor, record, assignee, note, follow_up_date=None):
    if actor.role not in LEADER_ROLES:
        raise PermissionError("Only school leadership can assign welfare follow-up tasks.")
    if assignee.role not in CARE_ROLES | LEADER_ROLES:
        raise ValueError("Follow-up can only be assigned to Patron, Matron, or school leadership.")
    before = record.case_state
    record.assigned_to_id = assignee.id
    record.assigned_note = note
    record.follow_up_required = True
    if follow_up_date:
        record.follow_up_date = follow_up_date
    record.case_state = "follow_up"
    record.updated_at = now_string()
    write_audit("Follow-up assigned", record=record, student=record.student, before=before, after="follow_up", reason=note)
    notify_users([assignee.id], "Welfare", f"Follow-up assigned: {record.student_name}", note, "/welfare")
    return record


def decide_approval(actor, record, approved, note):
    if actor.role not in LEADER_ROLES:
        raise PermissionError("Only school leadership can approve welfare actions.")
    before = record.approval_status
    record.approval_status = "approved" if approved else "declined"
    record.approved_by_id = actor.id
    record.approved_at = now_string()
    record.approval_note = note
    record.reviewed_by_id = actor.id
    record.reviewed_at = now_string()
    if approved:
        record.case_state = "follow_up" if record.follow_up_required else "open"
    else:
        record.case_state = "open"
    record.updated_at = now_string()
    write_audit(
        "Welfare action approved" if approved else "Welfare action declined",
        record=record, student=record.student, before=before, after=record.approval_status, reason=note,
    )
    notify_users([record.reporter_id], "Welfare", f"Action {record.approval_status}: {record.student_name}", note or record.approval_status, "/welfare")
    return record


def resolve_case(actor, record, note):
    if actor.role not in LEADER_ROLES:
        raise PermissionError("Only school leadership can close welfare cases after review.")
    before = record.case_state
    record.case_state = "resolved"
    record.resolved_by_id = actor.id
    record.resolved_at = now_string()
    record.resolution_note = note
    record.updated_at = now_string()
    write_audit("Welfare case resolved", record=record, student=record.student, before=before, after="resolved", reason=note)
    return record


def missing_reports_for(day):
    submitted = {row.reporter_role for row in DailyWelfareReport.query.filter_by(report_date=day).all()}
    missing = []
    for role in ("patron", "matron"):
        if role not in submitted and User.query.filter_by(role=role, is_active_account=True).first():
            missing.append(role)
    return missing


def notify_missing_daily_reports(day=None):
    day = day or datetime.date.today().isoformat()
    missing = missing_reports_for(day)
    if not missing:
        return 0
    labels = ", ".join(role.replace("_", " ").title() for role in missing)
    notify_school_admins(
        "Welfare",
        f"Missing daily welfare report ({day})",
        f"No daily welfare report has been submitted yet for: {labels}.",
        "/welfare",
    )
    return len(missing)


def notify_overdue_follow_ups(today=None):
    today = today or datetime.date.today().isoformat()
    overdue = StudentWelfareRecord.query.filter(
        StudentWelfareRecord.case_state != "resolved",
        StudentWelfareRecord.follow_up_required.is_(True),
        StudentWelfareRecord.follow_up_date.isnot(None),
        StudentWelfareRecord.follow_up_date < today,
    ).all()
    for record in overdue:
        notify_school_admins(
            "Welfare",
            f"Overdue welfare follow-up: {record.student_name}",
            f"Follow-up was due on {record.follow_up_date}.",
            "/welfare",
        )
        if record.assigned_to_id:
            notify_users(
                [record.assigned_to_id],
                "Welfare",
                f"Overdue follow-up: {record.student_name}",
                f"Follow-up was due on {record.follow_up_date}.",
                "/welfare",
            )
        elif record.reporter_id:
            notify_users(
                [record.reporter_id],
                "Welfare",
                f"Overdue follow-up: {record.student_name}",
                f"Follow-up was due on {record.follow_up_date}.",
                "/welfare",
            )
    return len(overdue)
