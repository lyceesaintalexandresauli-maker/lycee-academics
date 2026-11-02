from app.extensions import db
from app.models import AcademicSubject, DayScheduleEntry, TimetableEntry, User


def _login_as_master_admin(app, client):
    with app.app_context():
        admin = User(
            username="placement_forms_admin",
            full_name="Placement Forms Admin",
            password_hash="test-hash",
            role="master_admin",
            is_active_account=True,
        )
        db.session.add(admin)
        db.session.commit()
        admin_id = admin.id

    with client.session_transaction() as session:
        session["_user_id"] = str(admin_id)
        session["_fresh"] = True


def test_academic_forms_use_department_trade_level_and_class_selects(app, client):
    _login_as_master_admin(app, client)

    for path in ("/timetable", "/day-schedule", "/academic-management", "/assessments"):
        response = client.get(path)

        assert response.status_code == 200
        for field in ("department", "trade", "level", "class_name"):
            assert f'name="{field}"'.encode() in response.data

    assert b'<input class="form-control" name="class_name"' not in response.data


def test_timetable_rejects_mismatched_academic_placement(app, client):
    _login_as_master_admin(app, client)

    response = client.post(
        "/timetable",
        data={
            "department": "Fashion and Design",
            "trade": "Software Development",
            "level": "L4",
            "class_name": "L4 Software Development A",
            "day_of_week": "Monday",
            "subject": "Software Development",
        },
    )

    assert response.status_code == 200
    with app.app_context():
        assert TimetableEntry.query.count() == 0


def test_day_schedule_all_school_scope_and_invalid_partial_placement(app, client):
    _login_as_master_admin(app, client)

    response = client.post(
        "/day-schedule",
        data={
            "schedule_date": "2026-01-15",
            "activity": "School assembly",
        },
    )

    assert response.status_code == 302
    with app.app_context():
        entry = DayScheduleEntry.query.one()
        assert entry.class_name is None

    response = client.post(
        "/day-schedule",
        data={
            "schedule_date": "2026-01-16",
            "department": "ICT and Multimedia",
            "activity": "Incomplete placement",
        },
    )

    assert response.status_code == 200
    with app.app_context():
        assert DayScheduleEntry.query.count() == 1


def test_academic_subject_rejects_mismatched_department(app, client):
    _login_as_master_admin(app, client)

    response = client.post(
        "/academic-management",
        data={
            "action": "add_subject",
            "department": "Fashion and Design",
            "trade": "Software Development",
            "level": "L4",
            "class_name": "L4 Software Development A",
            "subject": "Programming",
        },
    )

    assert response.status_code == 200
    with app.app_context():
        assert AcademicSubject.query.count() == 0
