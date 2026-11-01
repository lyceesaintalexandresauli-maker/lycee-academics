from app.extensions import db
from app.models import BehaviorRecord, StudentGuardian, User, UserNotification


def make_user(username, role, **attributes):
    user = User(
        username=username,
        full_name=username.replace("_", " ").title(),
        password_hash="test-hash",
        role=role,
        is_active_account=True,
        **attributes,
    )
    db.session.add(user)
    db.session.flush()
    return user


def login_as(client, user):
    with client.session_transaction() as session:
        session["_user_id"] = str(user.id)
        session["_fresh"] = True


def test_teacher_can_submit_behavior_only_for_assigned_class(app):
    teacher = make_user("teacher", "teacher", class_name="L4 Software")
    assigned_student = make_user("assigned_student", "student", class_name="L4 Software")
    other_student = make_user("other_student", "student", class_name="L5 Software")
    db.session.commit()

    client = app.test_client()
    login_as(client, teacher)
    response = client.post("/behavior", data={
        "action": "create",
        "student_id": str(assigned_student.id),
        "record_type": "Positive",
        "title": "Helped classmates",
        "description": "Supported classmates during group work.",
    })
    assert response.status_code == 302
    assert BehaviorRecord.query.count() == 1
    record = BehaviorRecord.query.one()
    assert record.student_id == assigned_student.id
    assert record.status == "submitted"
    assert not record.is_published

    rejected = client.post("/behavior", data={
        "action": "create",
        "student_id": str(other_student.id),
        "record_type": "Concern",
        "title": "Out of scope",
        "description": "Should not be stored.",
    })
    assert rejected.status_code == 404
    assert BehaviorRecord.query.count() == 1


def test_parent_only_sees_published_records_for_verified_child(app):
    parent = make_user("parent", "parent")
    child = make_user("child", "student", class_name="L4", parent_id=parent.id)
    unrelated = make_user("unrelated", "student", class_name="L4")
    db.session.add(StudentGuardian(
        student_id=child.id,
        guardian_id=parent.id,
        relationship="Parent",
        status="verified",
        verified_at="2026-10-29 08:00:00",
    ))
    records = [
        BehaviorRecord(student_id=child.id, student_name=child.full_name, reporter_id=parent.id,
                       reporter_role="teacher", record_type="Positive", title="Published", description="Visible",
                       status="submitted", is_published=True, created_at="2026-10-29 08:00:00",
                       updated_at="2026-10-29 08:00:00"),
        BehaviorRecord(student_id=child.id, student_name=child.full_name, reporter_id=parent.id,
                       reporter_role="teacher", record_type="Concern", title="Draft", description="Hidden",
                       status="submitted", is_published=False, created_at="2026-10-29 09:00:00",
                       updated_at="2026-10-29 09:00:00"),
        BehaviorRecord(student_id=unrelated.id, student_name=unrelated.full_name, reporter_id=parent.id,
                       reporter_role="teacher", record_type="Serious", title="Unrelated", description="Hidden too",
                       status="submitted", is_published=True, created_at="2026-10-29 10:00:00",
                       updated_at="2026-10-29 10:00:00"),
    ]
    db.session.add_all(records)
    db.session.commit()

    client = app.test_client()
    login_as(client, parent)
    response = client.get("/behavior")
    assert response.status_code == 200
    assert b"Published" in response.data
    assert b"Draft" not in response.data
    assert b"Unrelated" not in response.data


def test_patron_scope_is_limited_to_assigned_class_and_boys(app):
    patron = make_user("patron", "patron", class_name="L4", gender="Male")
    boy = make_user("boy", "student", class_name="L4", gender="Male")
    girl = make_user("girl", "student", class_name="L4", gender="Female")
    other_class_boy = make_user("other_class_boy", "student", class_name="L5", gender="Male")
    db.session.commit()

    client = app.test_client()
    login_as(client, patron)
    allowed = client.post("/behavior", data={
        "action": "create", "student_id": str(boy.id), "record_type": "Concern",
        "title": "Needs support", "description": "Follow up with student.",
    })
    assert allowed.status_code == 302
    for student in (girl, other_class_boy):
        denied = client.post("/behavior", data={
            "action": "create", "student_id": str(student.id), "record_type": "Concern",
            "title": "Out of scope", "description": "Should not be stored.",
        })
        assert denied.status_code == 404
    assert BehaviorRecord.query.count() == 1


def test_admin_can_review_resolve_and_publish_with_requested_parent_alert(app):
    admin = make_user("school_admin", "master_admin")
    parent = make_user("child_parent", "parent")
    student = make_user("reported_student", "student", class_name="L4", parent_id=parent.id)
    record = BehaviorRecord(
        student_id=student.id,
        student_name=student.full_name,
        class_name=student.class_name,
        reporter_id=admin.id,
        reporter_role="teacher",
        record_type="Concern",
        title="Needs follow-up",
        description="The student needs support with classroom routines.",
        parent_notification_required=True,
        parent_notification_status="pending",
        status="submitted",
        created_at="2026-10-29 08:00:00",
        updated_at="2026-10-29 08:00:00",
    )
    db.session.add(record)
    db.session.commit()

    client = app.test_client()
    login_as(client, admin)
    review = client.post("/behavior", data={"action": "review", "record_id": record.id})
    assert review.status_code == 302
    db.session.refresh(record)
    assert record.status == "under_review"

    resolve = client.post("/behavior", data={
        "action": "resolve", "record_id": record.id, "resolution": "Counseling follow-up scheduled."
    })
    assert resolve.status_code == 302
    db.session.refresh(record)
    assert record.status == "resolved"
    assert record.resolved_by_id == admin.id

    publish = client.post("/behavior", data={"action": "publish", "record_id": record.id})
    assert publish.status_code == 302
    db.session.refresh(record)
    assert record.is_published
    assert record.parent_notification_status == "queued"
    assert UserNotification.query.filter_by(user_id=parent.id, category="Behavior").count() == 1
    assert UserNotification.query.filter_by(user_id=student.id, category="Behavior").count() == 1


def test_serious_behavior_cannot_be_published_before_review(app):
    admin = make_user("review_admin", "master_admin")
    student = make_user("serious_student", "student", class_name="L4")
    record = BehaviorRecord(
        student_id=student.id,
        student_name=student.full_name,
        class_name=student.class_name,
        reporter_id=admin.id,
        reporter_role="teacher",
        record_type="Critical",
        title="Safety concern",
        description="Requires authorized review.",
        status="submitted",
        created_at="2026-10-29 08:00:00",
        updated_at="2026-10-29 08:00:00",
    )
    db.session.add(record)
    db.session.commit()

    client = app.test_client()
    login_as(client, admin)
    rejected_publish = client.post("/behavior", data={"action": "publish", "record_id": record.id})
    assert rejected_publish.status_code == 302
    db.session.refresh(record)
    assert not record.is_published
    assert record.status == "submitted"

    client.post("/behavior", data={"action": "review", "record_id": record.id})
    db.session.refresh(record)
    assert record.status == "under_review"
    published = client.post("/behavior", data={"action": "publish", "record_id": record.id})
    assert published.status_code == 302
    db.session.refresh(record)
    assert record.is_published
