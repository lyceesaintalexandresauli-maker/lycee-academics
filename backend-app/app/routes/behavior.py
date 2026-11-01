import datetime

from flask import abort, flash, redirect, request, url_for
from flask_login import current_user
from markupsafe import escape

from app.extensions import db
from app.models import ActivityLog, BehaviorRecord, User
from app.utils.decorators import permission_for
from app.utils.helpers import linked_children, now_string, teacher_assigned_classes
from app.utils.notifications import notify_student_and_parent
from app.utils.rendering import page


REVIEW_ROLES = {"master_admin", "head_teacher", "discipline"}
CREATE_ROLES = REVIEW_ROLES | {"teacher", "patron", "matron"}
RECORD_TYPES = ("Positive", "Concern", "Serious", "Critical")
STATUS_LABELS = {
    "submitted": "Submitted",
    "under_review": "Under review",
    "resolved": "Resolved",
}


def _gender_values(role):
    if role == "patron":
        return {"male", "m", "boy"}
    if role == "matron":
        return {"female", "f", "girl"}
    return set()


def _scoped_students():
    query = User.query.filter_by(role="student")
    role = current_user.role
    if role in REVIEW_ROLES:
        return query
    if role == "teacher":
        names = {name.casefold() for name in teacher_assigned_classes(current_user)}
        return query.filter(db.func.lower(User.class_name).in_(names)) if names else query.filter(db.false())
    if role in {"patron", "matron"}:
        genders = _gender_values(role)
        if not current_user.class_name or not genders:
            return query.filter(db.false())
        return query.filter(
            db.func.lower(User.class_name) == current_user.class_name.casefold(),
            db.func.lower(User.gender).in_(genders),
        )
    if role == "student":
        return query.filter_by(id=current_user.id)
    if role == "parent":
        child_ids = [child.id for child in linked_children(current_user.id)]
        return query.filter(User.id.in_(child_ids)) if child_ids else query.filter(db.false())
    return query.filter(db.false())


def _audit(student, action, details):
    db.session.add(ActivityLog(
        actor_id=current_user.id,
        actor_name=current_user.full_name,
        student_id=student.id,
        student_name=student.full_name,
        action=action,
        details=details,
    ))


def behavior():
    can_create = current_user.role in CREATE_ROLES
    can_review = current_user.role in REVIEW_ROLES
    allowed_students = _scoped_students()
    allowed_ids = [student_id for (student_id,) in allowed_students.with_entities(User.id).all()]

    if request.method == "POST":
        action = request.form.get("action", "create").strip()
        if action == "create":
            if not can_create:
                abort(403)
            student_id = request.form.get("student_id", type=int)
            student = allowed_students.filter(User.id == student_id).first() if student_id else None
            record_type = request.form.get("record_type", "").strip()
            title = request.form.get("title", "").strip()
            description = request.form.get("description", "").strip()
            location = request.form.get("location", "").strip()
            follow_up_date = request.form.get("follow_up_date", "").strip()
            follow_up_required = request.form.get("follow_up_required") == "yes"
            parent_notification_required = request.form.get("parent_notification_required") == "yes"
            if not student:
                abort(404)
            if record_type not in RECORD_TYPES or not title or not description:
                flash("Choose a valid category and provide a title and description.", "danger")
            elif len(title) > 160 or len(location) > 160:
                flash("Title and location must be 160 characters or fewer.", "danger")
            elif follow_up_required and not follow_up_date:
                flash("Enter a follow-up date when follow-up is required.", "danger")
            else:
                if follow_up_date:
                    try:
                        datetime.date.fromisoformat(follow_up_date)
                    except ValueError:
                        flash("Enter a valid follow-up date.", "danger")
                        return redirect(url_for("behavior"))
                timestamp = now_string()
                record = BehaviorRecord(
                    student_id=student.id,
                    student_name=student.full_name,
                    class_name=student.class_name,
                    department=student.department,
                    trade=student.trade,
                    level=student.level,
                    academic_year=student.academic_year,
                    reporter_id=current_user.id,
                    reporter_role=current_user.role,
                    record_type=record_type,
                    title=title,
                    description=description,
                    location=location or None,
                    action_taken=request.form.get("action_taken", "").strip() or None,
                    follow_up_required=follow_up_required,
                    follow_up_date=follow_up_date or None,
                    parent_notification_required=parent_notification_required,
                    parent_notification_status="pending" if parent_notification_required else "not_required",
                    status="submitted",
                    created_at=timestamp,
                    updated_at=timestamp,
                )
                db.session.add(record)
                db.session.flush()
                _audit(student, "behavior_record_created", f"Behavior report #{record.id} submitted: {record_type} — {title}")
                db.session.commit()
                flash("Behavior report submitted for authorized review.", "success")
                return redirect(url_for("behavior"))
        elif action in {"review", "resolve", "publish"}:
            if not can_review:
                abort(403)
            record = db.session.get(BehaviorRecord, request.form.get("record_id", type=int)) or abort(404)
            if record.student_id not in allowed_ids:
                abort(403)
            timestamp = now_string()
            student = db.session.get(User, record.student_id) or abort(404)
            if action == "review":
                if record.status == "resolved":
                    abort(409)
                record.status = "under_review"
                record.updated_at = timestamp
                _audit(student, "behavior_record_review_started", f"Behavior report #{record.id} moved under review.")
            elif action == "resolve":
                resolution = request.form.get("resolution", "").strip()
                if not resolution:
                    flash("Add a resolution note before closing this behavior report.", "danger")
                    return redirect(url_for("behavior"))
                record.status = "resolved"
                record.resolution = resolution
                record.resolved_by_id = current_user.id
                record.resolved_at = timestamp
                record.updated_at = timestamp
                _audit(student, "behavior_record_resolved", f"Behavior report #{record.id} resolved: {resolution}")
            else:
                if record.record_type in {"Serious", "Critical"} and record.status == "submitted":
                    flash("Move serious or critical reports into review before publishing them.", "danger")
                    return redirect(url_for("behavior"))
                if not record.is_published:
                    record.is_published = True
                    record.updated_at = timestamp
                    if record.parent_notification_required and record.parent_notification_status == "pending":
                        notify_student_and_parent(
                            student, "Behavior", f"Behavior update: {record.title}",
                            f"{record.record_type}: {record.description}", "/discipline",
                        )
                        record.parent_notification_status = "queued"
                    _audit(student, "behavior_record_published", f"Behavior report #{record.id} published.")
            db.session.commit()
            flash("Behavior report updated.", "success")
            return redirect(url_for("behavior"))
        else:
            abort(400)

    if current_user.role in {"student", "parent"}:
        records_query = BehaviorRecord.query.filter(
            BehaviorRecord.student_id.in_(allowed_ids), BehaviorRecord.is_published.is_(True)
        )
    else:
        records_query = BehaviorRecord.query.filter(BehaviorRecord.student_id.in_(allowed_ids)) if allowed_ids else BehaviorRecord.query.filter(db.false())
    records = records_query.order_by(BehaviorRecord.created_at.desc(), BehaviorRecord.id.desc()).limit(500).all()

    students = allowed_students.order_by(User.full_name).all() if can_create else []
    student_options = "".join(
        f"<option value='{student.id}'>{escape(student.full_name)} ({escape(student.class_name or 'No class')})</option>"
        for student in students
    )
    type_options = "".join(f"<option>{value}</option>" for value in RECORD_TYPES)
    form = ""
    if can_create:
        form = f"""<section class='panel'><h2>Record behavior</h2><form method='post' class='row g-3'>
<input type='hidden' name='action' value='create'>
<div class='col-md-6'><label for='behavior-student'>Student</label><select class='form-select' id='behavior-student' name='student_id' required><option value=''>Choose student</option>{student_options}</select></div>
<div class='col-md-6'><label for='behavior-type'>Category</label><select class='form-select' id='behavior-type' name='record_type' required>{type_options}</select></div>
<div class='col-md-6'><label for='behavior-title'>Title</label><input class='form-control' id='behavior-title' name='title' maxlength='160' required></div>
<div class='col-md-6'><label for='behavior-location'>Location</label><input class='form-control' id='behavior-location' name='location' maxlength='160'></div>
<div class='col-12'><label for='behavior-description'>Description</label><textarea class='form-control' id='behavior-description' name='description' rows='3' required></textarea></div>
<div class='col-12'><label for='behavior-action'>Immediate action taken</label><textarea class='form-control' id='behavior-action' name='action_taken' rows='2'></textarea></div>
<div class='col-md-4'><label><input type='checkbox' name='follow_up_required' value='yes'> Follow-up required</label></div>
<div class='col-md-4'><label for='behavior-follow-up'>Follow-up date</label><input class='form-control' id='behavior-follow-up' type='date' name='follow_up_date'></div>
<div class='col-md-4'><label><input type='checkbox' name='parent_notification_required' value='yes'> Request parent notification after review</label></div>
<div class='col-12'><button class='btn btn-accent'>Submit for review</button></div></form></section>"""

    rows = []
    for record in records:
        controls = escape(STATUS_LABELS.get(record.status, record.status))
        if can_review:
            publish_control = (
                "<button class='btn btn-sm btn-outline-warning' name='action' value='publish'>Publish</button>"
                if not record.is_published else "Published"
            )
            controls = f"""<form method='post' class='d-flex flex-wrap gap-2 align-items-center'>
<input type='hidden' name='record_id' value='{record.id}'>
<button class='btn btn-sm btn-outline-primary' name='action' value='review'>Review</button>
<input class='form-control form-control-sm' name='resolution' maxlength='1000' placeholder='Resolution note'>
<button class='btn btn-sm btn-outline-success' name='action' value='resolve'>Resolve</button>
{publish_control}
</form>"""
        rows.append(
            f"<tr><td>{escape(record.created_at)}</td><td>{escape(record.student_name)}</td>"
            f"<td>{escape(record.class_name or '—')}</td><td>{escape(record.record_type)}</td>"
            f"<td>{escape(record.title)}</td><td>{escape(record.description)}</td>"
            f"<td>{escape(record.reporter.full_name if record.reporter else '—')}</td>"
            f"<td>{escape(STATUS_LABELS.get(record.status, record.status))}{' · Published' if record.is_published else ''}</td>"
            f"<td>{controls}</td></tr>"
        )
    heading = "My child’s published behavior reports" if current_user.role == "parent" else "My published behavior reports" if current_user.role == "student" else "Behavior reports in your authorized scope"
    body = f"""<section class='panel'><h1>Student <span class='accent'>Behavior</span></h1>
<p class='muted'>Behavior observations are separate from attendance, academic marks, and disciplinary decisions. Serious and critical reports require authorized human review.</p></section>
{form}<section class='panel'><h2>{escape(heading)}</h2><div class='table-responsive'><table class='table align-middle'><thead><tr><th>Reported</th><th>Student</th><th>Class</th><th>Category</th><th>Title</th><th>Description</th><th>Reporter</th><th>Status</th><th>Review</th></tr></thead><tbody>{''.join(rows) or '<tr><td colspan="9" class="muted">No behavior reports are available in this scope.</td></tr>'}</tbody></table></div></section>"""
    return page("Behavior", body, "behavior")


def register_routes(app):
    app.add_url_rule(
        "/behavior", endpoint="behavior", view_func=permission_for("behavior")(behavior),
        methods=["GET", "POST"],
    )
