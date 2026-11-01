import datetime
from app.extensions import db
from app.models import User
from app.services.welfare_service import create_welfare_record


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


def test_debug_admin(app, client):
    admin = make_user("admin_dbg", "master_admin")
    patron = make_user("patron_dbg", "patron", gender="male")
    print("ADMIN ID:", admin.id, "ROLE:", admin.role)
    print("PATRON ID:", patron.id, "ROLE:", patron.role)

    with client.session_transaction() as session:
        session["_user_id"] = str(patron.id)
        session["_fresh"] = True

    resp = client.get("/welfare/admin")
    print("PATRON STATUS:", resp.status_code)
    from flask_login import current_user
    with app.test_request_context("/"):
        from flask_login import login_user
        login_user(patron)
        print("CURRENT_USER ROLE:", current_user.role, "in LEADER:", current_user.role in {"master_admin", "head_teacher"})
    assert resp.status_code == 403
