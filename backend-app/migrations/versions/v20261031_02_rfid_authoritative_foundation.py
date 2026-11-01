"""Authoritative RFID physical attendance foundation migration.

Creates physical card lifecycle tracking, registered RFID readers/devices,
raw scan logs, attendance audit trails, and expands attendance statuses.
"""

from datetime import datetime
from sqlalchemy import inspect, text
from app.extensions import db
from app.models.rfid import RFIDCard, RFIDDevice, RFIDScanLog
from app.models.attendance import AttendanceAuditTrail


def upgrade(connection):
    inspector = inspect(connection)

    # 1. Create new tables if not present
    db.metadata.create_all(bind=connection, tables=[
        RFIDCard.__table__,
        RFIDDevice.__table__,
        RFIDScanLog.__table__,
        AttendanceAuditTrail.__table__,
    ])

    # 2. Add columns to attendance table
    if inspector.has_table("attendance"):
        attendance_cols = {col["name"] for col in inspector.get_columns("attendance")}
        additions = [
            ("session_name", "VARCHAR(30) DEFAULT 'morning'"),
            ("device_id", "VARCHAR(64)"),
            ("card_uid", "VARCHAR(100)"),
            ("is_corrected", "BOOLEAN DEFAULT FALSE"),
            ("correction_reason", "TEXT"),
            ("corrected_at", "VARCHAR(26)"),
            ("explanation", "TEXT"),
            ("explanation_approved_by", "INTEGER REFERENCES user(id)"),
        ]
        for col_name, col_type in additions:
            if col_name not in attendance_cols:
                connection.execute(text(f"ALTER TABLE attendance ADD COLUMN {col_name} {col_type}"))

    # 3. Seed/backfill RFID cards from existing User and PendingCard records
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if inspector.has_table("rfid_card"):
        # Sync student cards
        if inspector.has_table("user"):
            students_with_cards = connection.execute(text(
                'SELECT id, rfid_uid FROM "user" WHERE rfid_uid IS NOT NULL AND TRIM(rfid_uid) != \'\''
            )).fetchall()
            for s_id, s_uid in students_with_cards:
                norm_uid = str(s_uid).strip().replace(" ", "").upper()
                exists = connection.execute(
                    text("SELECT id FROM rfid_card WHERE card_uid = :uid"), {"uid": norm_uid}
                ).first()
                if not exists:
                    connection.execute(text(
                        "INSERT INTO rfid_card (card_uid, student_id, status, issued_at, created_at) "
                        "VALUES (:uid, :sid, 'Active', :now, :now)"
                    ), {"uid": norm_uid, "sid": s_id, "now": now_str})

        # Sync pending / lost cards
        if inspector.has_table("pending_card"):
            pending_rows = connection.execute(text(
                "SELECT uid, state, first_seen FROM pending_card"
            )).fetchall()
            for p_uid, p_state, p_first in pending_rows:
                norm_uid = str(p_uid).strip().replace(" ", "").upper()
                exists = connection.execute(
                    text("SELECT id FROM rfid_card WHERE card_uid = :uid"), {"uid": norm_uid}
                ).first()
                if not exists:
                    card_status = "Lost" if p_state == "Lost" else "Pending"
                    connection.execute(text(
                        "INSERT INTO rfid_card (card_uid, status, created_at, notes) "
                        "VALUES (:uid, :status, :created, 'Migrated from PendingCard queue')"
                    ), {"uid": norm_uid, "status": card_status, "created": p_first or now_str})

        # Ensure default device exists
        if inspector.has_table("rfid_device"):
            device_exists = connection.execute(text("SELECT id FROM rfid_device LIMIT 1")).first()
            if not device_exists:
                connection.execute(text(
                    "INSERT INTO rfid_device (device_id, device_name, device_token, location, device_type, is_active, created_at) "
                    "VALUES ('MAIN_GATE_01', 'Main Campus Gate Reader', 'muhura-gate-token-2026', 'Main Entrance', 'Gate', 1, :now)"
                ), {"now": now_str})
