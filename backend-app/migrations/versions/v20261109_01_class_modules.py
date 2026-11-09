"""Create persisted curriculum modules for the Classes & Modules page."""
from app.extensions import db
from app.models.academics import ClassModule
from sqlalchemy import inspect, text


def upgrade(connection):
    db.metadata.create_all(bind=connection, tables=[ClassModule.__table__])
    columns = {column["name"] for column in inspect(connection).get_columns("class_module")}
    if "teacher_id" not in columns:
        connection.execute(text("ALTER TABLE class_module ADD COLUMN teacher_id INTEGER REFERENCES user (id)"))
        connection.execute(text("CREATE INDEX IF NOT EXISTS ix_class_module_teacher_id ON class_module (teacher_id)"))
    if "is_active" not in columns:
        connection.execute(text("ALTER TABLE class_module ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT TRUE"))
