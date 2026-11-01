import datetime
from contextlib import contextmanager

from app.extensions import db
from app.models import User
from app.models.welfare import StudentWelfareRecord, DailyWelfareReport, WelfareAuditEvent
from app.services.welfare_service import (
    create_welfare_record,
    record_return,
    submit_daily_report,
    scoped_students_for_role,
    student_in_scope,
)
from app.services.welfare_analytics_service import repeated_concerns, answer_ai_question
from app.services.welfare_report_service import consolidated_report_for_day, send_consolidated_report
from flask_login import login_user


def make_user(username, role, *, name=None, gender=None, class_name=None, trade=None, level=None, sdms_code=None):
    user = User(
        username=username,
        full_name=name or username.title(),
        password_hash="test-only-hash",
        role=role,
        gender=gender,
        class_name=class_name,
        trade=trade,
        level=level,
        sdms_code=sdms_code,
        is_active_account=True,
    )
    db.session.add(user)
    db.session.flush()
    return user


@contextmanager
def as_user(app, user):
    """Run code with current_user bound to `user` (for direct service calls)."""
    with app.test_request_context("/"):
        login_user(user)
        yield


def login_as(client, user):
    with client.session_transaction() as session:
        session["_user_id"] = str(user.id)
        session["_fresh"] = True


def make_welfare_record(actor, student, status="sick_at_school", details="Test concern", day=None):
    day = day or datetime.date.today().isoformat()
    return create_welfare_record(actor, student, {
        "status": status,
        "details": details,
        "event_date": day,
        "expected_return_date": None,
        "follow_up_required": False,
        "follow_up_date": None,
        "follow_up_notes": "",
        "notify_guardian": False,
        "authorization_by": None,
        "authorization_note": None,
        "requires_admin_approval": False,
    })


# ---------------------------------------------------------------------------
# Role and gender permissions
# ---------------------------------------------------------------------------

def test_patron_sees_only_male_students(app):
    patron = make_user("patron_one", "patron", gender="male")
    matron = make_user("matron_one", "matron", gender="female")
    boy = make_user("boy_one", "student", gender="male", class_name="L3 SWD")
    girl = make_user("girl_one", "student", gender="female", class_name="L3 SWD")

    with app.app_context():
        patron_scope = {s.id for s in scoped_students_for_role("patron")}
        matron_scope = {s.id for s in scoped_students_for_role("matron")}
        assert boy.id in patron_scope
        assert girl.id not in patron_scope
        assert girl.id in matron_scope
        assert boy.id not in matron_scope


def test_matron_sees_only_female_students(app):
    matron = make_user("matron_two", "matron", gender="female")
    boy = make_user("boy_two", "student", gender="male", class_name="L4 NIT")
    girl = make_user("girl_two", "student", gender="female", class_name="L4 NIT")

    with app.app_context():
        matron_scope = {s.id for s in scoped_students_for_role("matron")}
        assert girl.id in matron_scope
        assert boy.id not in matron_scope


def test_admin_sees_all_students(app):
    admin = make_user("admin_welfare", "master_admin")
    boy = make_user("boy_three", "student", gender="male")
    girl = make_user("girl_three", "student", gender="female")

    with app.app_context():
        admin_scope = {s.id for s in scoped_students_for_role("master_admin")}
        assert boy.id in admin_scope
        assert girl.id in admin_scope


def test_teacher_has_no_welfare_scope(app):
    teacher = make_user("teacher_welfare", "teacher", gender="male")
    boy = make_user("boy_four", "student", gender="male")

    with app.app_context():
        assert not student_in_scope(boy, teacher)


def test_patron_cannot_access_girls_welfare_record(app):
    patron = make_user("patron_block", "patron", gender="male")
    girl = make_user("girl_block", "student", gender="female")

    with app.app_context():
        try:
            create_welfare_record(patron, girl, {"status": "sick_at_school", "details": "x", "event_date": datetime.date.today().isoformat()})
            assert False, "Should have raised PermissionError"
        except PermissionError:
            pass


# ---------------------------------------------------------------------------
# Endpoint permissions via test client
# ---------------------------------------------------------------------------

def test_welfare_index_patron(app, client):
    patron = make_user("patron_idx", "patron", gender="male")
    login_as(client, patron)
    resp = client.get("/welfare")
    assert resp.status_code == 200


def test_welfare_index_teacher_blocked(app, client):
    teacher = make_user("teacher_idx", "teacher")
    login_as(client, teacher)
    resp = client.get("/welfare")
    assert resp.status_code == 403


def test_welfare_index_student_blocked(app, client):
    student = make_user("student_idx", "student")
    login_as(client, student)
    resp = client.get("/welfare")
    assert resp.status_code == 403


def test_welfare_admin_only(app, client):
    admin = make_user("admin_w", "master_admin")
    login_as(client, admin)
    resp = client.get("/welfare/admin")
    assert resp.status_code == 200

    patron = make_user("patron_w", "patron", gender="male")
    login_as(client, patron)
    resp = client.get("/welfare/admin")
    assert resp.status_code == 403


def test_welfare_create_patron(app, client):
    patron = make_user("patron_c", "patron", gender="male")
    boy = make_user("boy_c", "student", gender="male", class_name="L3 SWD")
    login_as(client, patron)
    resp = client.post("/welfare/create", data={
        "student_id": boy.id,
        "status": "sick_at_school",
        "details": "Headache and fever.",
        "event_date": datetime.date.today().isoformat(),
    }, follow_redirects=True)
    assert resp.status_code == 200
    with app.app_context():
        assert StudentWelfareRecord.query.filter_by(student_id=boy.id).count() == 1


def test_welfare_create_patron_cannot_girl(app, client):
    patron = make_user("patron_c2", "patron", gender="male")
    girl = make_user("girl_c2", "student", gender="female")
    login_as(client, patron)
    resp = client.post("/welfare/create", data={
        "student_id": girl.id,
        "status": "sick_at_school",
        "details": "Should be blocked.",
        "event_date": datetime.date.today().isoformat(),
    })
    assert resp.status_code == 403


def test_welfare_student_view(app, client):
    patron = make_user("patron_v", "patron", gender="male")
    boy = make_user("boy_v", "student", gender="male", sdms_code="SDMS-1234")
    login_as(client, patron)
    resp = client.get(f"/welfare/student/{boy.id}")
    assert resp.status_code == 200
    assert b"SDMS-1234" in resp.data


def test_welfare_student_view_cross_gender_blocked(app, client):
    patron = make_user("patron_v2", "patron", gender="male")
    girl = make_user("girl_v2", "student", gender="female")
    login_as(client, patron)
    resp = client.get(f"/welfare/student/{girl.id}")
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Search and filters
# ---------------------------------------------------------------------------

def test_welfare_search_filters(app, client):
    patron = make_user("patron_s", "patron", gender="male")
    boy_swd = make_user("boy_swd", "student", gender="male", class_name="L3 Software Development", trade="Software Development", level="L3", sdms_code="SDMS-AAA")
    boy_nit = make_user("boy_nit", "student", gender="male", class_name="L4 Networking A", trade="Networking", level="L4", sdms_code="SDMS-BBB")
    login_as(client, patron)
    resp = client.get("/welfare/search?q=SDMS-AAA")
    assert resp.status_code == 200
    assert b"SDMS-AAA" in resp.data
    assert b"SDMS-BBB" not in resp.data

    resp = client.get("/welfare/search?trade=Networking")
    assert resp.status_code == 200
    assert b"SDMS-BBB" in resp.data
    assert b"SDMS-AAA" not in resp.data


def test_welfare_search_never_exposes_unauthorized(app, client):
    patron = make_user("patron_x", "patron", gender="male")
    girl = make_user("girl_x", "student", gender="female", sdms_code="SDMS-GIRL")
    login_as(client, patron)
    resp = client.get("/welfare/search?q=SDMS-GIRL")
    assert resp.status_code == 200
    assert b"SDMS-GIRL" not in resp.data


def test_api_students_enforces_scope(app, client):
    patron = make_user("patron_api", "patron", gender="male")
    boy = make_user("boy_api", "student", gender="male")
    girl = make_user("girl_api", "student", gender="female")
    login_as(client, patron)
    resp = client.get("/api/welfare/students")
    assert resp.status_code == 200
    data = resp.get_json()
    names = [s["name"] for s in data["students"]]
    assert boy.full_name in names
    assert girl.full_name not in names


# ---------------------------------------------------------------------------
# AI / repeated concerns analytics
# ---------------------------------------------------------------------------

def test_repeated_concerns_identifies_real_students(app):
    patron = make_user("patron_r", "patron", gender="male")
    boy = make_user("boy_r", "student", gender="male", class_name="L3 SWD")
    today = datetime.date.today()
    # Two sickness records within the window -> repeated.
    with app.app_context(), as_user(app, patron):
        r1 = make_welfare_record(patron, boy, "sick_at_school", "Fever.", day=today.isoformat())
        record_return(patron, r1, today.isoformat(), "Returned.")
        make_welfare_record(patron, boy, "sick_at_school", "Fever again.", day=(today - datetime.timedelta(days=5)).isoformat())
        db.session.commit()
        items = repeated_concerns(patron)
        assert len(items) == 1
        assert items[0]["student"].id == boy.id
        assert items[0]["record_count"] == 2


def test_ai_answer_repeated_concerns(app):
    patron = make_user("patron_ai", "patron", gender="male")
    boy = make_user("boy_ai", "student", gender="male", class_name="L3 SWD", sdms_code="SDMS-AI")
    today = datetime.date.today()
    with app.app_context(), as_user(app, patron):
        r1 = make_welfare_record(patron, boy, "sick_at_school", "Sick.", day=today.isoformat())
        record_return(patron, r1, today.isoformat(), "Returned.")
        make_welfare_record(patron, boy, "sick_at_school", "Sick again.", day=(today - datetime.timedelta(days=2)).isoformat())
        db.session.commit()
        result = answer_ai_question("Which assigned students have repeated welfare concerns?", patron)
        assert result["scope"] == "patron"
        assert any(s["student"] == boy.full_name for s in result["students"])
        assert any("SDMS-AI" in s["registration_number"] for s in result["students"])
        assert "evidence" in result


def test_ai_answer_respects_scope(app):
    patron = make_user("patron_scope_ai", "patron", gender="male")
    girl = make_user("girl_scope_ai", "student", gender="female")
    today = datetime.date.today()
    # Matron creates the girl's record (matron in-scope for girls), then the Patron AI must not see her.
    with app.app_context(), as_user(app, patron):
        # Patron cannot create a record for a girl.
        try:
            create_welfare_record(patron, girl, {
                "status": "sick_at_school", "details": "Sick.", "event_date": today.isoformat(),
                "expected_return_date": None, "follow_up_required": False, "follow_up_date": None,
                "follow_up_notes": "", "notify_guardian": False, "authorization_by": None,
                "authorization_note": None, "requires_admin_approval": False,
            })
            assert False, "Should have raised PermissionError"
        except PermissionError:
            pass
    matron = make_user("matron_scope", "matron", gender="female")
    with app.app_context(), as_user(app, matron):
        make_welfare_record(matron, girl, "sick_at_school", "Sick.", day=today.isoformat())
        make_welfare_record(matron, girl, "sick_at_school", "Sick again.", day=(today - datetime.timedelta(days=1)).isoformat())
        db.session.commit()
        result = answer_ai_question("Which assigned students have repeated welfare concerns?", patron)
        assert len(result["students"]) == 0


# ---------------------------------------------------------------------------
# Daily reports
# ---------------------------------------------------------------------------

def test_patron_and_matron_submit_separate_daily_reports(app):
    patron = make_user("patron_d", "patron", gender="male")
    matron = make_user("matron_d", "matron", gender="female")
    today = datetime.date.today().isoformat()
    with app.app_context(), as_user(app, patron):
        submit_daily_report(patron, today, "Boys observation.", "None.", "None.")
        db.session.commit()
    with app.app_context(), as_user(app, matron):
        submit_daily_report(matron, today, "Girls observation.", "None.", "None.")
        db.session.commit()
    patron_report = DailyWelfareReport.query.filter_by(reporter_role="patron", report_date=today).first()
    matron_report = DailyWelfareReport.query.filter_by(reporter_role="matron", report_date=today).first()
    assert patron_report is not None
    assert matron_report is not None
    assert patron_report.reporter_id == patron.id
    assert matron_report.reporter_id == matron.id


def test_daily_report_duplicate_blocked(app):
    patron = make_user("patron_dup", "patron", gender="male")
    today = datetime.date.today().isoformat()
    with app.app_context(), as_user(app, patron):
        submit_daily_report(patron, today, "First.", "None.", "None.")
        try:
            submit_daily_report(patron, today, "Second.", "None.", "None.")
            assert False, "Should raise ValueError"
        except ValueError:
            pass


def test_consolidated_report_includes_both_genders(app):
    patron = make_user("patron_con", "patron", gender="male")
    matron = make_user("matron_con", "matron", gender="female")
    boy = make_user("boy_con", "student", gender="male", class_name="L3 SWD")
    girl = make_user("girl_con", "student", gender="female", class_name="L4 NIT")
    today = datetime.date.today().isoformat()
    with app.app_context(), as_user(app, patron):
        make_welfare_record(patron, boy, "sick_at_school", "Sick boy.", day=today)
        make_welfare_record(matron, girl, "hospitalized", "Hospitalized girl.", day=today)
        db.session.commit()
        data = consolidated_report_for_day(today, patron)
        assert data["total_boys_concerns"] >= 1
        assert data["total_girls_concerns"] >= 1


def test_send_consolidated_report_delivers(app):
    admin = make_user("admin_send", "master_admin")
    patron = make_user("patron_send", "patron", gender="male")
    today = datetime.date.today().isoformat()
    with app.app_context():
        success, message = send_consolidated_report(admin, today)
        assert success is True
        # Audit event recorded
        from app.models.welfare import WelfareAuditEvent
        events = WelfareAuditEvent.query.filter_by(action="daily_report_delivered").all()
        assert len(events) >= 1


# ---------------------------------------------------------------------------
# Admin report history and download
# ---------------------------------------------------------------------------

def test_admin_report_history(app, client):
    admin = make_user("admin_hist", "master_admin")
    patron = make_user("patron_hist", "patron", gender="male")
    today = datetime.date.today().isoformat()
    with app.app_context(), as_user(app, patron):
        submit_daily_report(patron, today, "Obs.", "None.", "None.")
        db.session.commit()
    login_as(client, admin)
    resp = client.get("/welfare/reports")
    assert resp.status_code == 200
    assert b"Obs." in resp.data or today.encode() in resp.data


def test_admin_report_download(app, client):
    admin = make_user("admin_dl", "master_admin")
    patron = make_user("patron_dl", "patron", gender="male")
    today = datetime.date.today().isoformat()
    with app.app_context(), as_user(app, patron):
        submit_daily_report(patron, today, "Obs.", "None.", "None.")
        report = DailyWelfareReport.query.filter_by(reporter_role="patron", report_date=today).first()
        db.session.commit()
        rid = report.id
    login_as(client, admin)
    resp = client.get(f"/welfare/report/{rid}/download")
    assert resp.status_code == 200
    assert resp.mimetype == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def test_welfare_audit_logged(app, client):
    admin = make_user("admin_audit", "master_admin")
    patron = make_user("patron_audit", "patron", gender="male")
    boy = make_user("boy_audit", "student", gender="male")
    with app.app_context(), as_user(app, patron):
        make_welfare_record(patron, boy, "sick_at_school", "Audit test.", day=datetime.date.today().isoformat())
        db.session.commit()
    login_as(client, admin)
    resp = client.get("/welfare/audit")
    assert resp.status_code == 200
    assert b"Audit test" in resp.data or b"Welfare record created" in resp.data
