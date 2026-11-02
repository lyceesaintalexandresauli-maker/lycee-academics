from app.extensions import db
from app.models import AdmissionApplicant, User
from app.utils.academic_placement import (
    is_valid_academic_placement,
    render_academic_placement_fields,
)


def _login_as_master_admin(app, client):
    with app.app_context():
        admin = User(
            username="placement_admin",
            full_name="Placement Admin",
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


def test_academic_placement_fields_are_four_selects():
    fields = render_academic_placement_fields("test")

    for field in ("department", "trade", "level", "class_name"):
        assert f'name="{field}"' in fields
        assert f'<input name="{field}"' not in fields

    assert "data-department=" in fields
    assert "data-trade=" in fields
    assert "data-level=" in fields


def test_academic_placement_must_follow_school_hierarchy():
    assert is_valid_academic_placement(
        "ICT and Multimedia",
        "Software Development",
        "L4",
        "L4 Software Development A",
    )
    assert not is_valid_academic_placement(
        "Fashion and Design",
        "Software Development",
        "L4",
        "L4 Software Development A",
    )


def test_admissions_uses_dropdowns_and_rejects_mismatched_placement(app, client):
    _login_as_master_admin(app, client)

    response = client.get("/admissions")

    assert response.status_code == 200
    for field in ("department", "trade", "level", "class_name"):
        assert f'name="{field}"'.encode() in response.data
    assert b'name="department" list=' not in response.data

    response = client.post(
        "/admissions",
        data={
            "action": "create",
            "full_name": "Invalid Placement Applicant",
            "department": "Fashion and Design",
            "trade": "Software Development",
            "level": "L4",
            "class_name": "L4 Software Development A",
        },
    )

    assert response.status_code == 302
    with app.app_context():
        assert AdmissionApplicant.query.count() == 0


def test_student_registration_uses_academic_dropdowns(app, client):
    _login_as_master_admin(app, client)

    response = client.get("/students")

    assert response.status_code == 200
    for field in ("department", "trade", "level", "class_name"):
        assert f'name="{field}"'.encode() in response.data
    assert b'name="department" list=' not in response.data
    assert b'id="class-name"' not in response.data


def test_teacher_assignment_uses_and_validates_four_placement_dropdowns(app, client):
    _login_as_master_admin(app, client)

    response = client.get("/admin")

    assert response.status_code == 200
    for field in (
        "assignment_department[]",
        "assignment_trade[]",
        "assignment_level[]",
        "assignment_class[]",
    ):
        assert f'name="{field}"'.encode() in response.data
    assert b"Trade / Department" not in response.data

    response = client.post(
        "/admin",
        data={
            "action": "create_staff",
            "username": "invalid_placement_teacher",
            "full_name": "Invalid Placement Teacher",
            "password": "valid-password",
            "role": "teacher",
            "assignment_department[]": "Fashion and Design",
            "assignment_trade[]": "Software Development",
            "assignment_level[]": "L4",
            "assignment_class[]": "L4 Software Development A",
            "assignment_subject[]": "Software Development",
        },
    )

    assert response.status_code == 302
    with app.app_context():
        assert User.query.filter_by(username="invalid_placement_teacher").first() is None

    response = client.post(
        "/admin",
        data={
            "action": "create_staff",
            "username": "valid_placement_teacher",
            "full_name": "Valid Placement Teacher",
            "password": "valid-password",
            "role": "teacher",
            "assignment_department[]": "ICT and Multimedia",
            "assignment_trade[]": "Software Development",
            "assignment_level[]": "L4",
            "assignment_class[]": "L4 Software Development A",
            "assignment_subject[]": "Software Development",
        },
    )

    assert response.status_code == 302
    with app.app_context():
        teacher = User.query.filter_by(username="valid_placement_teacher").one()
        assert teacher.class_name == "L4 Software Development A"
