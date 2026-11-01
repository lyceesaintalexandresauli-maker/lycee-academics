"""Welfare Intelligence routes — Patron / Matron / Admin.

Built on the existing welfare models and services. Enforces role- and
gender-based permissions on every endpoint, backed by real database records.
"""

import datetime
import json

from flask import (
    abort,
    flash,
    jsonify,
    redirect,
    render_template_string,
    request,
    url_for,
)
from flask_login import current_user, login_required
from markupsafe import escape

from app.extensions import db
from app.models import User
from app.models.welfare import (
    CASE_STATES,
    DailyWelfareReport,
    StudentWelfareRecord,
    WelfareAuditEvent,
)
from app.utils.decorators import permission_for
from app.utils.helpers import get_setting, now_string, set_setting
from app.utils.rendering import page
from app.services import welfare_service as ws
from app.services.welfare_analytics_service import (
    answer_ai_question,
    authorized_students,
    group_summary,
    repeated_concerns,
    student_summary,
    welfare_records_for_student,
)
from app.services.welfare_report_service import (
    consolidated_report_for_day,
    report_history,
    send_consolidated_report,
)

CARE_ROLES = {"patron", "matron"}
LEADER_ROLES = {"master_admin", "head_teacher"}

REPORT_STATUS_CATEGORIES = (
    "sick_at_school",
    "hospitalized",
    "sent_home",
    "authorized_leave",
    "welfare_concern",
    "follow_up_required",
    "recovered",
    "other",
)


def _gender_filter_for_role(role):
    if role == "patron":
        return {"male", "m", "boy"}
    if role == "matron":
        return {"female", "f", "girl"}
    return None


def _scope_filter(student_ids):
    if current_user.role in LEADER_ROLES:
        return student_ids
    genders = _gender_filter_for_role(current_user.role)
    if not genders:
        return []
    return [
        sid
        for sid in student_ids
        if User.query.get(sid) and (User.query.get(sid).gender or "").strip().casefold() in genders
    ]


def _student_options(students):
    return "".join(
        f"<option value='{s.id}'>{escape(s.full_name)}</option>" for s in students
    )


def _catalog_options(trades, levels, classes):
    trade_html = "".join(f"<option value='{escape(t)}'>{escape(t)}</option>" for t in trades)
    level_html = "".join(f"<option value='{escape(l)}'>{escape(l)}</option>" for l in levels)
    class_html = "".join(f"<option value='{escape(c)}'>{escape(c)}</option>" for c in classes)
    return trade_html, level_html, class_html


def _student_rows_html(students):
    rows = []
    for s in students:
        inferred_trade, inferred_level = None, None
        try:
            from app.utils.constants import CLASS_TRADE_LEVEL

            inferred_trade, inferred_level = CLASS_TRADE_LEVEL.get(s.class_name, (None, None))
        except Exception:
            pass
        rows.append(
            f"<tr><td>{escape(s.full_name)}</td><td>{escape(s.sdms_code or '-')}</td>"
            f"<td>{escape(s.trade or inferred_trade or '-')}</td>"
            f"<td>{escape(s.level or inferred_level or '-')}</td>"
            f"<td>{escape(s.class_name or '-')}</td>"
            f"<td><a class='btn btn-sm btn-outline-success' href='{url_for('welfare_student', student_id=s.id)}'>View</a></td></tr>"
        )
    return "".join(rows)


def _base_panel(title, intro, body):
    return f"""<section class="panel"><h1>{title}</h1><p class="muted">{intro}</p>{body}</section>"""


def welfare_index():
    if current_user.role not in CARE_ROLES | LEADER_ROLES:
        abort(403)
    role = current_user.role
    gender_label = "Boys" if role == "patron" else "Girls" if role == "matron" else "All students"
    students = authorized_students()
    student_ids = [s.id for s in students]
    today = datetime.date.today().isoformat()

    # Current active welfare by status.
    active_by_status = {}
    active_records = StudentWelfareRecord.query.filter(
        StudentWelfareRecord.student_id.in_(student_ids),
        StudentWelfareRecord.status.in_(ws.LOCATION_STATUSES),
        StudentWelfareRecord.case_state != "resolved",
        StudentWelfareRecord.actual_return_date.is_(None),
    ).all() if student_ids else []
    for r in active_records:
        active_by_status[r.status] = active_by_status.get(r.status, 0) + 1

    unresolved = StudentWelfareRecord.query.filter(
        StudentWelfareRecord.student_id.in_(student_ids),
        StudentWelfareRecord.case_state != "resolved",
    ).all() if student_ids else []
    overdue_return = [
        r for r in active_records
        if r.expected_return_date
        and datetime.date.fromisoformat(r.expected_return_date[:10]) < datetime.date.today()
        and not r.actual_return_date
        and r.status in {"sent_home", "authorized_leave"}
    ]
    urgent = [r for r in active_records if r.is_urgent or r.status in ws.URGENT_STATUSES]

    stats_html = f"""
    <div class="grid mb-4">
      <div class="stat"><div class="stat-value">{len(students)}</div><div class="stat-label">Authorized {gender_label}</div></div>
      <div class="stat"><div class="stat-value">{len(active_records)}</div><div class="stat-label">Active welfare records</div></div>
      <div class="stat"><div class="stat-value">{len(unresolved)}</div><div class="stat-label">Unresolved cases</div></div>
      <div class="stat"><div class="stat-value">{len(overdue_return)}</div><div class="stat-label">Overdue return dates</div></div>
      <div class="stat"><div class="stat-value">{len(urgent)}</div><div class="stat-label">Urgent / hospitalized</div></div>
    </div>"""

    recent_rows = ""
    for r in sorted(unresolved, key=lambda x: x.event_date or "", reverse=True)[:8]:
        s = User.query.get(r.student_id)
        recent_rows += f"<tr><td>{escape(r.event_date)}</td><td>{escape(s.full_name if s else '?')}</td><td>{escape(r.class_name or '-')}</td><td><span class='pill'>{escape(ws.STATUS_LABELS.get(r.status, r.status))}</span></td><td>{escape(ws.CASE_LABELS.get(r.case_state, r.case_state))}</td><td><a class='btn btn-sm btn-outline-success' href='{url_for('welfare_student', student_id=r.student_id)}'>View</a></td></tr>"
    recent_html = f"""
    <section class="panel"><h2>Recent Welfare Cases</h2>
    <div class="table-responsive"><table class="table align-middle"><thead><tr><th>Date</th><th>Student</th><th>Class</th><th>Status</th><th>Case State</th><th>Action</th></tr></thead><tbody>{recent_rows or '<tr><td colspan="6" class="muted">No recent welfare cases.</td></tr>'}</tbody></table></div></section>"""

    body = stats_html + recent_html

    # Quick actions by role.
    actions = ""
    if role in CARE_ROLES:
        actions += f"<a class='btn btn-accent' href='{url_for('welfare_create')}'>Record Welfare Case</a>"
        actions += f"<a class='btn btn-outline-success' href='{url_for('welfare_daily_submit')}'>Submit Daily Report</a>"
    if role in LEADER_ROLES:
        actions += f"<a class='btn btn-outline-success' href='{url_for('welfare_admin')}'>Admin Welfare Dashboard</a>"
    if actions:
        body = f"<div class='d-flex gap-2 flex-wrap mb-3'>{actions}</div>" + body

    return page("Welfare Intelligence", _base_panel("Welfare Intelligence", f"Manage welfare for your authorized {gender_label} students.", body), "dashboard")


def welfare_search():
    """Advanced search / filter: Department → Trade → Level → Class → Student."""
    if current_user.role not in CARE_ROLES | LEADER_ROLES:
        abort(403)
    from app.utils.constants import CLASS_GROUPS, CLASS_TRADE_LEVEL, TRADES, PROGRAM_LEVELS

    students = authorized_students()
    q = (request.args.get("q") or "").strip()
    status = (request.args.get("status") or "").strip()
    trade = (request.args.get("trade") or "").strip()
    level = (request.args.get("level") or "").strip()
    class_name = (request.args.get("class") or "").strip()

    results = students
    if q:
        ql = q.casefold()
        results = [s for s in results if ql in (s.full_name or "").casefold() or ql in (s.sdms_code or "").casefold() or ql in (s.username or "").casefold()]
    if status:
        results = [s for s in results if _active_status_matches(s.id, status)]
    if trade:
        results = [s for s in results if (s.trade or "").casefold() == trade.casefold()]
    if level:
        results = [s for s in results if (s.level or "").casefold() == level.casefold()]
    if class_name:
        results = [s for s in results if (s.class_name or "").casefold() == class_name.casefold()]

    # Available filter values scoped to authorized students.
    trades = sorted({s.trade for s in students if s.trade})
    levels = sorted({s.level for s in students if s.level})
    classes = sorted({s.class_name for s in students if s.class_name})
    trade_opts, level_opts, class_opts = _catalog_options(trades, levels, classes)
    student_opts = _student_options(students)

    rows_html = _student_rows_html(results)

    status_opts = "".join(
        f"<option value='{escape(v)}'{' selected' if v == status else ''}>{escape(ws.STATUS_LABELS.get(v, v))}</option>"
        for v in REPORT_STATUS_CATEGORIES
    )

    body = f"""<section class="panel"><h1>Student Welfare Search</h1><p class="muted">Filter authorized students by department, trade, level, class, name, registration number, SDMS code, or welfare status.</p>
    <form method="get" class="row g-3 mb-4">
      <input type="hidden" name="action" value="search">
      <div class="col-md-3"><label>Student / SDMS / Registration</label><input class="form-control" name="q" value="{escape(q)}" placeholder="Search by name, registration number, or SDMS code"></div>
      <div class="col-md-2"><label>Trade</label><select class="form-select" name="trade"><option value="">Any trade</option>{trade_opts}</select></div>
      <div class="col-md-2"><label>Level</label><select class="form-select" name="level"><option value="">Any level</option>{level_opts}</select></div>
      <div class="col-md-2"><label>Class</label><select class="form-select" name="class"><option value="">Any class</option>{class_opts}</select></div>
      <div class="col-md-2"><label>Welfare Status</label><select class="form-select" name="status"><option value="">Any status</option>{status_opts}</select></div>
      <div class="col-12 d-flex align-items-end gap-2"><button class="btn btn-accent">Apply Filters</button><a class="btn btn-outline-secondary" href="{url_for('welfare_search')}">Clear Filters</a></div>
    </form>
    <div class="table-responsive"><table class="table align-middle"><thead><tr><th>Student</th><th>SDMS Code</th><th>Trade</th><th>Level</th><th>Class</th><th>Action</th></tr></thead><tbody>{rows_html or '<tr><td colspan="6" class="muted">No students match the selected filters.</td></tr>'}</tbody></table></div>
    <p class="muted">{len(results)} student(s) found within your authorized scope.</p></section>"""

    return page("Student Welfare Search", _base_panel("Student Welfare Search", "Filter and locate authorized students.", body), "dashboard")


def _active_status_matches(student_id, status):
    records = StudentWelfareRecord.query.filter_by(student_id=student_id).order_by(StudentWelfareRecord.id.desc()).all()
    for r in records:
        if r.status == status:
            return True
    return False


def welfare_create():
    """Record a new welfare case (Patron/Matron only, gender-scoped)."""
    if current_user.role not in CARE_ROLES:
        abort(403)
    students = authorized_students()
    student_opts = _student_options(students)

    if request.method == "POST":
        student_id = request.form.get("student_id", type=int)
        student = db.session.get(User, student_id)
        if not student or not ws.student_in_scope(student, current_user):
            abort(403)
        payload = {
            "status": request.form.get("status", "").strip(),
            "details": request.form.get("details", "").strip(),
            "event_date": request.form.get("event_date", "").strip() or datetime.date.today().isoformat(),
            "expected_return_date": request.form.get("expected_return_date", "").strip() or None,
            "follow_up_required": request.form.get("follow_up_required") == "on",
            "follow_up_date": request.form.get("follow_up_date", "").strip() or None,
            "follow_up_notes": request.form.get("follow_up_notes", "").strip(),
            "notify_guardian": request.form.get("notify_guardian") == "on",
            "authorization_by": request.form.get("authorization_by", "").strip() or None,
            "authorization_note": request.form.get("authorization_note", "").strip(),
            "requires_admin_approval": request.form.get("requires_admin_approval") == "on",
        }
        if not payload["status"] or payload["status"] not in ws.LOCATION_STATUSES | {"welfare_concern"}:
            flash("Choose a valid welfare status.", "danger")
        elif not payload["details"]:
            flash("Describe the welfare concern.", "danger")
        else:
            try:
                ws.create_welfare_record(current_user, student, payload)
                db.session.commit()
                flash("Welfare case recorded.", "success")
                return redirect(url_for("welfare_student", student_id=student.id))
            except (PermissionError, ValueError) as exc:
                db.session.rollback()
                flash(str(exc), "danger")

    status_opts = "".join(
        f"<option value='{escape(v)}'>{escape(ws.STATUS_LABELS.get(v, v))}</option>"
        for v in sorted(ws.LOCATION_STATUSES | {"welfare_concern"})
    )
    body = f"""<section class="panel"><h1>Record Welfare Case</h1><p class="muted">Create a welfare record for one of your authorized students. This does not change RFID attendance.</p>
    <form method="post" class="row g-3">
      <div class="col-md-4"><label>Student</label><select class="form-select" name="student_id" required>{student_opts}</select></div>
      <div class="col-md-3"><label>Welfare Category</label><select class="form-select" name="status" required>{status_opts}</select></div>
      <div class="col-md-3"><label>Event Date</label><input class="form-control" type="date" name="event_date" value="{datetime.date.today().isoformat()}" required></div>
      <div class="col-md-2"><label>Expected Return Date</label><input class="form-control" type="date" name="expected_return_date"></div>
      <div class="col-12"><label>Details / Concern</label><textarea class="form-control" name="details" rows="3" required></textarea></div>
      <div class="col-md-3"><label>Follow-up Required</label><input type="checkbox" name="follow_up_required"></div>
      <div class="col-md-3"><label>Follow-up Date</label><input class="form-control" type="date" name="follow_up_date"></div>
      <div class="col-md-3"><label>Follow-up Notes</label><input class="form-control" name="follow_up_notes"></div>
      <div class="col-md-3"><label>Notify Parent / Guardian</label><input type="checkbox" name="notify_guardian"></div>
      <div class="col-md-3"><label>Authorized By</label><input class="form-control" name="authorization_by"></div>
      <div class="col-md-3"><label>Authorization Note</label><input class="form-control" name="authorization_note"></div>
      <div class="col-md-3"><label>Requires Admin Approval</label><input type="checkbox" name="requires_admin_approval"></div>
      <div class="col-12"><button class="btn btn-accent">Record Welfare Case</button></div>
    </form></section>"""
    return page("Record Welfare Case", _base_panel("Record Welfare Case", "Create a new welfare case for an authorized student.", body), "dashboard")


def welfare_student(student_id):
    """Individual student welfare intelligence profile."""
    if current_user.role not in CARE_ROLES | LEADER_ROLES:
        abort(403)
    student = db.session.get(User, student_id)
    if not student or student.role != "student" or not ws.student_in_scope(student, current_user):
        abort(403)
    summary = student_summary(student, current_user)

    records_html = ""
    for r in summary["records"]:
        badge_class = "pill"
        if r["is_urgent"]:
            badge_class += " bg-danger text-white"
        records_html += f"""<tr><td>{escape(r['date'])}</td><td><span class='{badge_class}'>{escape(r['status_label'])}</span></td><td>{escape(r['case_state_label'])}</td><td>{escape(r['details'])}</td><td>{escape(r['reported_by'])}</td><td>{escape(r['expected_return_date'] or '-')}</td><td>{escape(r['actual_return_date'] or '-')}</td><td>{'Yes' if r['follow_up_required'] else 'No'}</td><td>{'Yes' if r['resolved'] else 'No'}</td></tr>"""

    active = summary["active_welfare"]
    active_html = f"<span class='pill bg-danger text-white'>{escape(ws.STATUS_LABELS.get(active.status, active.status))}</span>" if active else "<span class='muted'>None</span>"

    body = f"""<section class="panel"><h1>Student Welfare: {escape(student.full_name)}</h1><p class="muted">{escape(student.sdms_code or 'No SDMS code')} · {escape(student.trade or '-')} · {escape(student.level or '-')} · {escape(student.class_name or '-')}</p>
    <div class="grid mb-4">
      <div class="stat"><div class="stat-value">{summary['total_reports']}</div><div class="stat-label">Total Welfare Reports</div></div>
      <div class="stat"><div class="stat-value">{summary['sick_count']}</div><div class="stat-label">Sick at School</div></div>
      <div class="stat"><div class="stat-value">{summary['hospitalized_count']}</div><div class="stat-label">Hospitalized</div></div>
      <div class="stat"><div class="stat-value">{summary['home_count']}</div><div class="stat-label">Sent Home / Leave</div></div>
      <div class="stat"><div class="stat-value">{summary['unresolved_count']}</div><div class="stat-label">Unresolved Cases</div></div>
    </div>
    <div class="d-flex gap-2 mb-3"><strong>Latest Status:</strong> {active_html}</div>
    <section class="panel"><h2>Welfare History</h2>
    <div class="table-responsive"><table class="table align-middle"><thead><tr><th>Date</th><th>Status</th><th>Case State</th><th>Details</th><th>Reported By</th><th>Expected Return</th><th>Actual Return</th><th>Follow-up</th><th>Resolved</th></tr></thead><tbody>{records_html or '<tr><td colspan="9" class="muted">No welfare records for this student.</td></tr>'}</tbody></table></div></section></section>"""
    return page(f"Welfare: {escape(student.full_name)}", _base_panel(f"Welfare: {escape(student.full_name)}", "Complete welfare history and intelligence for this student.", body), "dashboard")


def welfare_group(scope):
    """Trade / level / class welfare intelligence."""
    if current_user.role not in CARE_ROLES | LEADER_ROLES:
        abort(403)
    name = request.args.get("name", "").strip()
    if not name:
        abort(400)

    # Resolve student ids for this group from the roster, then enforce gender scope.
    students = authorized_students()
    if scope == "class":
        ids = [s.id for s in students if (s.class_name or "").casefold() == name.casefold()]
    elif scope == "level":
        ids = [s.id for s in students if (s.level or "").casefold() == name.casefold()]
    elif scope == "trade":
        ids = [s.id for s in students if (s.trade or "").casefold() == name.casefold()]
    else:
        abort(400)

    data = group_summary(ids, current_user)
    rows_html = ""
    for row in data["students"]:
        s = row["student"]
        rows_html += f"""<tr><td>{escape(s.full_name)}</td><td>{escape(s.sdms_code or '-')}</td><td>{escape(s.class_name or '-')}</td><td>{row['total_reports']}</td><td>{row['unresolved']}</td><td><span class='pill'>{escape(row['active_label'] or '-')}</span></td><td>{'Repeated' if row['repeated'] else 'No'}</td><td>{'Overdue' if row['overdue_return'] else 'No'}</td><td><a class='btn btn-sm btn-outline-success' href='{url_for('welfare_student', student_id=s.id)}'>View</a></td></tr>"""

    totals = data["totals"]
    body = f"""<section class="panel"><h1>{escape(scope.title())} Welfare: {escape(name)}</h1><p class="muted">Welfare analysis for all authorized students in this {scope}.</p>
    <div class="grid mb-4">
      <div class="stat"><div class="stat-value">{totals['enrolled']}</div><div class="stat-label">Enrolled Students</div></div>
      <div class="stat"><div class="stat-value">{totals['with_concerns']}</div><div class="stat-label">With Welfare Concerns</div></div>
      <div class="stat"><div class="stat-value">{totals['repeated']}</div><div class="stat-label">Repeated Concerns</div></div>
      <div class="stat"><div class="stat-value">{totals['hospitalized']}</div><div class="stat-label">Hospitalized</div></div>
      <div class="stat"><div class="stat-value">{totals['sick_at_school']}</div><div class="stat-label">Sick at School</div></div>
      <div class="stat"><div class="stat-value">{totals['at_home']}</div><div class="stat-label">At Home / Leave</div></div>
      <div class="stat"><div class="stat-value">{totals['overdue_return']}</div><div class="stat-label">Overdue Return</div></div>
      <div class="stat"><div class="stat-value">{totals['unresolved']}</div><div class="stat-label">Unresolved Cases</div></div>
      <div class="stat"><div class="stat-value">{totals['needs_follow_up']}</div><div class="stat-label">Needs Follow-up</div></div>
    </div>
    <div class="table-responsive"><table class="table align-middle"><thead><tr><th>Student</th><th>SDMS Code</th><th>Class</th><th>Reports</th><th>Unresolved</th><th>Active Status</th><th>Repeated</th><th>Overdue Return</th><th>Action</th></tr></thead><tbody>{rows_html or '<tr><td colspan="9" class="muted">No students in this group.</td></tr>'}</tbody></table></div></section>"""
    return page(f"{scope.title()} Welfare: {escape(name)}", _base_panel(f"{scope.title()} Welfare: {escape(name)}", f"Aggregate welfare picture for {escape(name)}.", body), "dashboard")


def welfare_daily_submit():
    """Patron/Matron submit the daily welfare report."""
    if current_user.role not in CARE_ROLES:
        abort(403)
    today = datetime.date.today().isoformat()
    existing = DailyWelfareReport.query.filter_by(reporter_role=current_user.role, report_date=today).first()
    if existing:
        flash(f"A daily welfare report for {today} has already been submitted.", "info")
        return redirect(url_for("welfare_index"))

    if request.method == "POST":
        observations = request.form.get("observations", "").strip()
        recommended_actions = request.form.get("recommended_actions", "").strip()
        serious_incidents = request.form.get("serious_incidents", "").strip()
        if not observations:
            flash("Enter observations for today's welfare report.", "danger")
        else:
            try:
                ws.submit_daily_report(current_user, today, observations, recommended_actions, serious_incidents)
                db.session.commit()
                flash("Daily welfare report submitted to the Administration.", "success")
                return redirect(url_for("welfare_index"))
            except (PermissionError, ValueError) as exc:
                db.session.rollback()
                flash(str(exc), "danger")

    # Quick summary to help the reporter.
    totals = ws.snapshot_totals(current_user.role, today)
    body = f"""<section class="panel"><h1>Submit Daily Welfare Report — {today}</h1><p class="muted">Submit the consolidated daily welfare snapshot for your authorized students before the configured deadline.</p>
    <div class="grid mb-4">
      <div class="stat"><div class="stat-value">{totals['total_students']}</div><div class="stat-label">Authorized Students</div></div>
      <div class="stat"><div class="stat-value">{totals['sick_count']}</div><div class="stat-label">Sick at School</div></div>
      <div class="stat"><div class="stat-value">{totals['hospitalized_count']}</div><div class="stat-label">Hospitalized</div></div>
      <div class="stat"><div class="stat-value">{totals['sent_home_count']}</div><div class="stat-label">Sent Home / Leave</div></div>
      <div class="stat"><div class="stat-value">{totals['follow_up_count']}</div><div class="stat-label">Follow-up Required</div></div>
      <div class="stat"><div class="stat-value">{totals['incident_count']}</div><div class="stat-label">Urgent Incidents</div></div>
    </div>
    <form method="post" class="row g-3">
      <div class="col-12"><label>Observations</label><textarea class="form-control" name="observations" rows="4" required></textarea></div>
      <div class="col-12"><label>Recommended Actions</label><textarea class="form-control" name="recommended_actions" rows="3"></textarea></div>
      <div class="col-12"><label>Serious Incidents</label><textarea class="form-control" name="serious_incidents" rows="3"></textarea></div>
      <div class="col-12"><button class="btn btn-accent">Submit Daily Report</button></div>
    </form></section>"""
    return page("Submit Daily Welfare Report", _base_panel("Submit Daily Welfare Report", f"Daily welfare report for {current_user.role.replace('_', ' ').title()}.", body), "dashboard")


def welfare_admin():
    """Admin welfare dashboard — consolidated boys + girls."""
    if current_user.role not in LEADER_ROLES:
        abort(403)
    today = datetime.date.today().isoformat()
    data = consolidated_report_for_day(today, current_user)
    history = report_history(limit=10, user=current_user)

    history_rows = ""
    for r in history:
        history_rows += f"""<tr><td>{escape(r['report_date'])}</td><td>{escape(r['reporter_role'].replace('_', ' ').title())}</td><td>{escape(r['reporter_name'])}</td><td>{escape(r['submitted_at'])}</td><td>{r['total_students']}</td><td>{r['sick_count']}</td><td>{r['hospitalized_count']}</td><td>{r['follow_up_count']}</td><td>{'Reviewed' if r['reviewed'] else 'Pending'}</td><td><a class='btn btn-sm btn-outline-success' href='{url_for('welfare_report_download', report_id=r.id)}'>Download</a></td></tr>"""

    body = f"""<section class="panel"><h1>Admin Welfare Dashboard</h1><p class="muted">Consolidated boys' and girls' welfare intelligence, daily reports, and case management.</p>
    <div class="grid mb-4">
      <div class="stat"><div class="stat-value">{data['total_boys_concerns']}</div><div class="stat-label">Boys with Concerns</div></div>
      <div class="stat"><div class="stat-value">{data['total_girls_concerns']}</div><div class="stat-label">Girls with Concerns</div></div>
      <div class="stat"><div class="stat-value">{data['repeated_count']}</div><div class="stat-label">Repeated Concerns</div></div>
      <div class="stat"><div class="stat-value">{len(data['urgent_students'])}</div><div class="stat-label">Urgent / Hospitalized</div></div>
      <div class="stat"><div class="stat-value">{len(data['overdue_return_students'])}</div><div class="stat-label">Overdue Returns</div></div>
      <div class="stat"><div class="stat-value">{len(data['unresolved_students'])}</div><div class="stat-label">Unresolved Cases</div></div>
    </div>
    <div class="d-flex gap-2 flex-wrap mb-3">
      <a class='btn btn-accent' href='{url_for('welfare_ai')}'>Welfare AI Assistant</a>
      <a class='btn btn-outline-success' href='{url_for('welfare_reports')}'>Report History</a>
      <a class='btn btn-outline-success' href='{url_for('welfare_settings')}'>Welfare Settings</a>
    </div>
    <section class="panel"><h2>Daily Report — {escape(today)}</h2>
    <div class="grid mb-3">
      <div class="stat"><div class="stat-value">{data['patron']['total_students']}</div><div class="stat-label">Boys Enrolled (Patron)</div></div>
      <div class="stat"><div class="stat-value">{data['matron']['total_students']}</div><div class="stat-label">Girls Enrolled (Matron)</div></div>
      <div class="stat"><div class="stat-value">{data['patron']['sick_count']}</div><div class="stat-label">Boys Sick at School</div></div>
      <div class="stat"><div class="stat-value">{data['matron']['sick_count']}</div><div class="stat-label">Girls Sick at School</div></div>
      <div class="stat"><div class="stat-value">{data['patron']['hospitalized_count']}</div><div class="stat-label">Boys Hospitalized</div></div>
      <div class="stat"><div class="stat-value">{data['matron']['hospitalized_count']}</div><div class="stat-label">Girls Hospitalized</div></div>
      <div class="stat"><div class="stat-value">{data['patron']['at_home_count']}</div><div class="stat-label">Boys At Home</div></div>
      <div class="stat"><div class="stat-value">{data['matron']['at_home_count']}</div><div class="stat-label">Girls At Home</div></div>
      <div class="stat"><div class="stat-value">{data['patron']['follow_up_count']}</div><div class="stat-label">Boys Follow-up</div></div>
      <div class="stat"><div class="stat-value">{data['matron']['follow_up_count']}</div><div class="stat-label">Girls Follow-up</div></div>
      <div class="stat"><div class="stat-value">{data['patron']['urgent_count']}</div><div class="stat-label">Boys Urgent</div></div>
      <div class="stat"><div class="stat-value">{data['matron']['urgent_count']}</div><div class="stat-label">Girls Urgent</div></div>
    </div>
    <div class="d-flex gap-2 mb-3">
      <span class='pill'>{'Patron Submitted' if data['patron']['submitted'] else 'Patron Missing'}</span>
      <span class='pill'>{'Matron Submitted' if data['matron']['submitted'] else 'Matron Missing'}</span>
    </div>
    {f"<div class='alert alert-danger'><strong>Missing submissions:</strong> {', '.join(data['missing_submissions'])}</div>" if data['missing_submissions'] else ''}
    {f"<div class='alert alert-warning'><strong>Late submissions:</strong> {', '.join(data['late_submissions'])}</div>" if data['late_submissions'] else ''}
    <div class="table-responsive"><table class="table align-middle"><thead><tr><th>Category</th><th>Boys</th><th>Girls</th><th>Total</th></tr></thead><tbody>
      <tr><td>Enrolled Students</td><td>{data['patron']['total_students']}</td><td>{data['matron']['total_students']}</td><td>{data['patron']['total_students'] + data['matron']['total_students']}</td></tr>
      <tr><td>Welfare Concerns</td><td>{data['total_boys_concerns']}</td><td>{data['total_girls_concerns']}</td><td>{data['total_boys_concerns'] + data['total_girls_concerns']}</td></tr>
      <tr><td>Repeated Concerns</td><td colspan="3">{data['repeated_count']} students: {', '.join(data['repeated_students']) or 'None'}</td></tr>
      <tr><td>Urgent / Hospitalized</td><td colspan="3">{', '.join(data['urgent_students']) or 'None'}</td></tr>
      <tr><td>Sick at School</td><td colspan="3">{', '.join(data['sick_students']) or 'None'}</td></tr>
      <tr><td>At Home / Leave</td><td colspan="3">{', '.join(data['home_students']) or 'None'}</td></tr>
      <tr><td>Overdue Returns</td><td colspan="3">{', '.join(data['overdue_return_students']) or 'None'}</td></tr>
      <tr><td>Unresolved Cases</td><td colspan="3">{', '.join(data['unresolved_students']) or 'None'}</td></tr>
    </tbody></table></div></section>
    <section class="panel"><h2>Daily Report History</h2>
    <div class="table-responsive"><table class="table align-middle"><thead><tr><th>Date</th><th>Reporter</th><th>Name</th><th>Submitted</th><th>Students</th><th>Sick</th><th>Hospitalized</th><th>Follow-up</th><th>Review</th><th>Action</th></tr></thead><tbody>{history_rows or '<tr><td colspan="10" class="muted">No daily welfare reports have been submitted yet.</td></tr>'}</tbody></table></div></section>"""
    return page("Admin Welfare Dashboard", _base_panel("Admin Welfare Dashboard", "Consolidated welfare oversight for the whole school.", body), "dashboard")


def welfare_reports():
    if current_user.role not in LEADER_ROLES:
        abort(403)
    history = report_history(limit=50, user=current_user)
    rows_html = ""
    for r in history:
        rows_html += f"""<tr><td>{escape(r['report_date'])}</td><td>{escape(r['reporter_role'].replace('_', ' ').title())}</td><td>{escape(r['reporter_name'])}</td><td>{escape(r['submitted_at'])}</td><td>{r['total_students']}</td><td>{r['sick_count']}</td><td>{r['hospitalized_count']}</td><td>{r['sent_home_count']}</td><td>{r['follow_up_count']}</td><td>{r['incident_count']}</td><td>{'Reviewed' if r['reviewed'] else 'Pending'}</td><td><a class='btn btn-sm btn-outline-success' href='{url_for('welfare_report_download', report_id=r['id'])}'>Download</a></td></tr>"""
    body = f"""<section class="panel"><h1>Welfare Report History</h1><p class="muted">Review and download previously generated daily welfare reports.</p>
    <div class="table-responsive"><table class="table align-middle"><thead><tr><th>Date</th><th>Reporter Role</th><th>Reporter</th><th>Submitted At</th><th>Students</th><th>Sick</th><th>Hospitalized</th><th>Sent Home</th><th>Follow-up</th><th>Incidents</th><th>Review</th><th>Action</th></tr></thead><tbody>{rows_html or '<tr><td colspan="12" class="muted">No welfare reports in history.</td></tr>'}</tbody></table></div></section>"""
    return page("Welfare Report History", _base_panel("Welfare Report History", "View and download historical daily welfare reports.", body), "dashboard")


def welfare_report_download(report_id):
    if current_user.role not in LEADER_ROLES:
        abort(403)
    report = db.session.get(DailyWelfareReport, report_id)
    if not report:
        abort(404)
    from openpyxl import Workbook
    from io import BytesIO
    wb = Workbook()
    ws_ = wb.active
    ws_.title = f"Welfare {report.report_date}"
    ws_.append(["Daily Welfare Report", report.report_date])
    ws_.append(["Reporter Role", report.reporter_role])
    ws_.append(["Reporter", report.reporter.full_name if report.reporter else "-"])
    ws_.append(["Submitted At", report.submitted_at])
    ws_.append([])
    ws_.append(["Total Students", report.total_students])
    ws_.append(["Sick Count", report.sick_count])
    ws_.append(["Hospitalized Count", report.hospitalized_count])
    ws_.append(["Sent Home Count", report.sent_home_count])
    ws_.append(["Follow-up Count", report.follow_up_count])
    ws_.append(["Incident Count", report.incident_count])
    ws_.append([])
    ws_.append(["Observations", report.observations])
    ws_.append(["Recommended Actions", report.recommended_actions or "-"])
    ws_.append(["Serious Incidents", report.serious_incidents or "-"])
    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)
    from flask import send_file
    return send_file(buf, mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", as_attachment=True, download_name=f"welfare_report_{report.report_date}.xlsx")


def welfare_ai():
    if current_user.role not in CARE_ROLES | LEADER_ROLES:
        abort(403)
    answer = None
    question = ""
    if request.method == "POST":
        question = (request.form.get("question") or "").strip()
        if question:
            result = answer_ai_question(question, current_user)
            answer = result
    rows_html = ""
    if answer:
        for s in answer.get("students", []):
            rows_html += f"""<tr><td>{escape(s['student'])}</td><td>{escape(s['registration_number'])}</td><td>{escape(s['class'])}</td><td>{escape(s['trade'])}</td><td>{escape(s['level'])}</td><td>{escape(s['latest_status'])}</td><td>{row_priority(s['priority'])}</td><td>{escape(s['latest_date'] or '-')}</td></tr>"""
    body = f"""<section class="panel"><h1>Welfare AI Assistant</h1><p class="muted">Ask welfare intelligence questions. Every answer is backed by real database records and respects your authorized scope.</p>
    <form method="post" class="row g-3 mb-4">
      <div class="col-md-8"><label>Question</label><input class="form-control" name="question" value="{escape(question)}" placeholder="e.g. Which assigned students have repeated welfare concerns?"></div>
      <div class="col-md-4"><button class="btn btn-accent">Ask</button></div>
    </form>
    {f"""<section class="panel"><h2>Answer</h2><div class="muted">Scope: {escape(answer['scope'])}</div><p>{escape(answer['answer'])}</p>
    <div class="table-responsive"><table class="table align-middle"><thead><tr><th>Student</th><th>SDMS Code</th><th>Class</th><th>Trade</th><th>Level</th><th>Latest Status</th><th>Priority</th><th>Latest Date</th></tr></thead><tbody>{rows_html or '<tr><td colspan="8" class="muted">No matching students.</td></tr>'}</tbody></table></div>
    {f"<div class='mt-3'><strong>Evidence:</strong><ul>{''.join(f'<li>{escape(e['date'])} — {escape(e['status_label'])}: {escape(e['details'])}</li>' for e in answer.get('evidence', []))}</ul></div>" if answer.get("evidence") else ""}</section>""" if answer else ""}
    <section class="panel"><h2>Example Questions</h2><ul class="muted"><li>Which assigned students have repeated welfare concerns?</li><li>Show me this student's welfare history.</li><li>Has this student been repeatedly sick?</li><li>When was the last welfare report submitted?</li><li>Does this student have an overdue follow-up?</li><li>Which welfare cases remain unresolved?</li><li>Which students need immediate follow-up?</li></ul></section>"""
    return page("Welfare AI Assistant", _base_panel("Welfare AI Assistant", "AI-powered welfare intelligence on real records.", body), "dashboard")


def row_priority(priority):
    classes = {"High": "bg-danger text-white", "Medium": "bg-warning text-dark", "Low": "bg-secondary text-white"}
    return f"<span class='pill {classes.get(priority, '')}'>{escape(priority)}</span>"


def welfare_settings():
    if current_user.role not in LEADER_ROLES:
        abort(403)
    if request.method == "POST":
        action = request.form.get("action", "")
        if action == "save_settings":
            min_count = request.form.get("min_count", "2").strip()
            period_days = request.form.get("period_days", "30").strip()
            hour = request.form.get("hour", "8").strip()
            minute = request.form.get("minute", "0").strip()
            try:
                int(min_count); int(period_days); int(hour); int(minute)
            except ValueError:
                flash("Enter valid numeric settings.", "danger")
            else:
                for key, value in (("welfare_repeated_min_count", min_count), ("welfare_repeated_period_days", period_days), ("welfare_daily_report_hour", hour), ("welfare_daily_report_minute", minute)):
                    set_setting(key, value)
                flash("Welfare settings saved.", "success")
                return redirect(url_for("welfare_settings"))
        elif action == "generate_report_today":
            success, message = send_consolidated_report(current_user, datetime.date.today().isoformat())
            flash(message, "success" if success else "danger")
            return redirect(url_for("welfare_settings"))

    min_count = get_setting("welfare_repeated_min_count", "2")
    period_days = get_setting("welfare_repeated_period_days", "30")
    hour = get_setting("welfare_daily_report_hour", "8")
    minute = get_setting("welfare_daily_report_minute", "0")
    body = f"""<section class="panel"><h1>Welfare Settings</h1><p class="muted">Configure repeated-concern thresholds and the daily report deadline.</p>
    <form method="post" class="row g-3 mb-4">
      <input type="hidden" name="action" value="save_settings">
      <div class="col-md-3"><label>Minimum reports for "repeated"</label><input class="form-control" type="number" name="min_count" min="1" value="{escape(min_count)}" required></div>
      <div class="col-md-3"><label>Repeated-concern window (days)</label><input class="form-control" type="number" name="period_days" min="1" value="{escape(period_days)}" required></div>
      <div class="col-md-3"><label>Daily report deadline hour</label><input class="form-control" type="number" name="hour" min="0" max="23" value="{escape(hour)}" required></div>
      <div class="col-md-3"><label>Daily report deadline minute</label><input class="form-control" type="number" name="minute" min="0" max="59" value="{escape(minute)}" required></div>
      <div class="col-12"><button class="btn btn-accent">Save Settings</button></div>
    </form>
    <section class="panel"><h2>Manual Report Generation</h2><p class="muted">Generate and deliver the consolidated daily welfare report to administrators now (for testing or immediate delivery).</p>
    <form method="post" class="d-flex gap-2"><input type="hidden" name="action" value="generate_report_today"><button class="btn btn-accent">Generate & Deliver Today's Report</button></form></section></section>"""
    return page("Welfare Settings", _base_panel("Welfare Settings", "Configure the welfare intelligence system.", body), "dashboard")


def welfare_audit():
    if current_user.role not in LEADER_ROLES:
        abort(403)
    events = WelfareAuditEvent.query.order_by(WelfareAuditEvent.created_at.desc()).limit(100).all()
    rows_html = ""
    for e in events:
        rows_html += f"""<tr><td>{escape(e.created_at)}</td><td>{escape(e.actor_name)}</td><td>{escape(e.action)}</td><td>{escape(e.student.full_name if e.student else '-')}</td><td>{escape(e.reason or '-')}</td></tr>"""
    body = f"""<section class="panel"><h1>Welfare Audit Log</h1><p class="muted">Immutable trail of welfare case, report, and access actions.</p>
    <div class="table-responsive"><table class="table align-middle"><thead><tr><th>Time</th><th>Actor</th><th>Action</th><th>Student</th><th>Reason</th></tr></thead><tbody>{rows_html or '<tr><td colspan="5" class="muted">No audit events yet.</td></tr>'}</tbody></table></div></section>"""
    return page("Welfare Audit Log", _base_panel("Welfare Audit Log", "Review welfare system audit history.", body), "dashboard")


# ---------------------------------------------------------------------------
# API endpoints (JSON) — all permission-enforced
# ---------------------------------------------------------------------------

def _json_students(students):
    return [
        {
            "id": s.id,
            "name": s.full_name,
            "registration_number": s.sdms_code,
            "username": s.username,
            "trade": s.trade,
            "level": s.level,
            "class_name": s.class_name,
            "gender": s.gender,
        }
        for s in students
    ]


def api_students():
    if current_user.role not in CARE_ROLES | LEADER_ROLES:
        return jsonify({"error": "forbidden"}), 403
    q = (request.args.get("q") or "").strip().casefold()
    status = (request.args.get("status") or "").strip()
    trade = (request.args.get("trade") or "").strip()
    level = (request.args.get("level") or "").strip()
    class_name = (request.args.get("class") or "").strip()

    results = authorized_students()
    if q:
        results = [s for s in results if q in (s.full_name or "").casefold() or q in (s.sdms_code or "").casefold() or q in (s.username or "").casefold()]
    if trade:
        results = [s for s in results if (s.trade or "").casefold() == trade.casefold()]
    if level:
        results = [s for s in results if (s.level or "").casefold() == level.casefold()]
    if class_name:
        results = [s for s in results if (s.class_name or "").casefold() == class_name.casefold()]
    if status:
        results = [s for s in results if _active_status_matches(s.id, status)]
    return jsonify({"students": _json_students(results), "count": len(results)})


def api_student_summary(student_id):
    if current_user.role not in CARE_ROLES | LEADER_ROLES:
        return jsonify({"error": "forbidden"}), 403
    student = db.session.get(User, student_id)
    if not student or student.role != "student" or not ws.student_in_scope(student, current_user):
        return jsonify({"error": "not_found_or_forbidden"}), 404
    summary = student_summary(student, current_user)
    return jsonify({
        "id": student.id,
        "name": student.full_name,
        "sdms_code": student.sdms_code,
        "trade": student.trade,
        "level": student.level,
        "class_name": student.class_name,
        "total_reports": summary["total_reports"],
        "sick_count": summary["sick_count"],
        "hospitalized_count": summary["hospitalized_count"],
        "home_count": summary["home_count"],
        "unresolved_count": summary["unresolved_count"],
        "records": summary["records"],
    })


def api_repeated_concerns():
    if current_user.role not in CARE_ROLES | LEADER_ROLES:
        return jsonify({"error": "forbidden"}), 403
    items = repeated_concerns(current_user)
    return jsonify({
        "count": len(items),
        "students": [
            {
                "id": i["student"].id,
                "name": i["student"].full_name,
                "class": i["student"].class_name,
                "trade": i["student"].trade,
                "level": i["student"].level,
                "record_count": i["record_count"],
                "priority": i["priority"],
                "latest_status": i["latest_status_label"],
                "latest_date": i["latest_date"],
                "unresolved_count": i["unresolved_count"],
                "overdue_return_count": i["overdue_return_count"],
            }
            for i in items
        ],
    })


def api_ai_answer():
    if current_user.role not in CARE_ROLES | LEADER_ROLES:
        return jsonify({"error": "forbidden"}), 403
    data = request.get_json(silent=True) or {}
    question = data.get("question", "")
    result = answer_ai_question(question, current_user)
    return jsonify(result)


def register_routes(app):
    app.add_url_rule("/welfare", endpoint="welfare", view_func=permission_for("welfare")(login_required(welfare_index)), methods=["GET"])
    app.add_url_rule("/welfare/search", endpoint="welfare_search", view_func=permission_for("welfare_search")(login_required(welfare_search)), methods=["GET"])
    app.add_url_rule("/welfare/create", endpoint="welfare_create", view_func=permission_for("welfare_create")(login_required(welfare_create)), methods=["GET", "POST"])
    app.add_url_rule("/welfare/student/<int:student_id>", endpoint="welfare_student", view_func=permission_for("welfare_student")(login_required(welfare_student)), methods=["GET"])
    app.add_url_rule("/welfare/group/<scope>", endpoint="welfare_group", view_func=permission_for("welfare_group")(login_required(welfare_group)), methods=["GET"])
    app.add_url_rule("/welfare/daily-submit", endpoint="welfare_daily_submit", view_func=permission_for("welfare_daily_submit")(login_required(welfare_daily_submit)), methods=["GET", "POST"])
    app.add_url_rule("/welfare/admin", endpoint="welfare_admin", view_func=permission_for("welfare_admin")(login_required(welfare_admin)), methods=["GET"])
    app.add_url_rule("/welfare/reports", endpoint="welfare_reports", view_func=permission_for("welfare_reports")(login_required(welfare_reports)), methods=["GET"])
    app.add_url_rule("/welfare/report/<int:report_id>/download", endpoint="welfare_report_download", view_func=permission_for("welfare_report_download")(login_required(welfare_report_download)), methods=["GET"])
    app.add_url_rule("/welfare/ai", endpoint="welfare_ai", view_func=permission_for("welfare_ai")(login_required(welfare_ai)), methods=["GET", "POST"])
    app.add_url_rule("/welfare/settings", endpoint="welfare_settings", view_func=permission_for("welfare_settings")(login_required(welfare_settings)), methods=["GET", "POST"])
    app.add_url_rule("/welfare/audit", endpoint="welfare_audit", view_func=permission_for("welfare_audit")(login_required(welfare_audit)), methods=["GET"])
    app.add_url_rule("/api/welfare/students", endpoint="api_welfare_students", view_func=permission_for("api_welfare_students")(login_required(api_students)), methods=["GET"])
    app.add_url_rule("/api/welfare/student/<int:student_id>", endpoint="api_welfare_student_summary", view_func=permission_for("api_welfare_student_summary")(login_required(api_student_summary)), methods=["GET"])
    app.add_url_rule("/api/welfare/repeated-concerns", endpoint="api_welfare_repeated_concerns", view_func=permission_for("api_welfare_repeated_concerns")(login_required(api_repeated_concerns)), methods=["GET"])
    app.add_url_rule("/api/welfare/ai-answer", endpoint="api_welfare_ai_answer", view_func=permission_for("api_welfare_ai_answer")(login_required(api_ai_answer)), methods=["POST"])
