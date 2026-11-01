from sqlalchemy import inspect

from app import create_app
from app.extensions import db
from app.models import School, SchoolClass


class FreshDatabaseConfig:
    TESTING = True
    SECRET_KEY = "test"
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SQLALCHEMY_TRACK_MODIFICATIONS = False


def test_create_app_initializes_fresh_database():
    app = create_app(FreshDatabaseConfig)

    with app.app_context():
        table_names = inspect(db.engine).get_table_names()

        assert "user" in table_names
        assert School.query.count() == 1
        assert SchoolClass.query.count() > 0

        db.drop_all()
