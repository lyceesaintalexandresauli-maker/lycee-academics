"""Create separate, auditable student behavior records."""

from sqlalchemy import inspect


def upgrade(connection):
    if not inspect(connection).has_table("user"):
        return

    from app.models.behavior import BehaviorRecord

    BehaviorRecord.__table__.create(bind=connection, checkfirst=True)
