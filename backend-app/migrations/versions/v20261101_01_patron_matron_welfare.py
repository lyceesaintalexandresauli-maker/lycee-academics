"""Create Patron and Matron student welfare tables."""

from sqlalchemy import inspect

from app.models.welfare import DailyWelfareReport, StudentWelfareRecord, WelfareAuditEvent


def upgrade(connection):
    if not inspect(connection).has_table("user"):
        return
    StudentWelfareRecord.__table__.create(bind=connection, checkfirst=True)
    DailyWelfareReport.__table__.create(bind=connection, checkfirst=True)
    WelfareAuditEvent.__table__.create(bind=connection, checkfirst=True)
