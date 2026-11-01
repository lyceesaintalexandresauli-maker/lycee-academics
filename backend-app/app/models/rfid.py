from app.extensions import db


class PendingCard(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    uid = db.Column(db.String(100), unique=True, nullable=False)
    first_seen = db.Column(db.String(19), nullable=False)
    last_seen = db.Column(db.String(26))
    state = db.Column(db.String(30), default="Pending")


class RFIDCard(db.Model):
    """Authoritative RFID physical card ledger and lifecycle tracking."""
    id = db.Column(db.Integer, primary_key=True)
    card_uid = db.Column(db.String(100), unique=True, nullable=False, index=True)
    student_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True, index=True)
    status = db.Column(db.String(30), nullable=False, default="Pending")  # Pending, Active, Lost, Replaced, Deactivated
    issued_at = db.Column(db.String(26), nullable=True)
    deactivated_at = db.Column(db.String(26), nullable=True)
    deactivation_reason = db.Column(db.String(255), nullable=True)
    replaced_by_card_id = db.Column(db.Integer, db.ForeignKey("rfid_card.id"), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.String(26), nullable=True)
    updated_at = db.Column(db.String(26), nullable=True)

    student = db.relationship("User", foreign_keys=[student_id], backref="rfid_cards")
    replaced_by = db.relationship("RFIDCard", remote_side=[id], foreign_keys=[replaced_by_card_id])


class RFIDDevice(db.Model):
    """Registered physical RFID readers, turnstiles, and scanners."""
    id = db.Column(db.Integer, primary_key=True)
    device_id = db.Column(db.String(64), unique=True, nullable=False, index=True)  # e.g. "MAIN_GATE_01"
    device_name = db.Column(db.String(100), nullable=False)
    device_token = db.Column(db.String(128), nullable=False)
    location = db.Column(db.String(120), nullable=False, default="Campus Gate")
    device_type = db.Column(db.String(50), nullable=False, default="Gate")  # Gate, Classroom, Dormitory, Mobile, Admin
    assigned_class = db.Column(db.String(100), nullable=True)  # optional class lock
    allowed_sessions = db.Column(db.String(100), nullable=True, default="morning,afternoon")
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    last_seen = db.Column(db.String(26), nullable=True)
    last_ip = db.Column(db.String(45), nullable=True)
    firmware_version = db.Column(db.String(50), nullable=True)
    created_at = db.Column(db.String(26), nullable=True)


class RFIDScanLog(db.Model):
    """Immutable raw physical tap event ledger for audit trail and duplicate protection."""
    id = db.Column(db.Integer, primary_key=True)
    card_uid = db.Column(db.String(100), nullable=False, index=True)
    student_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True, index=True)
    device_id = db.Column(db.String(64), nullable=True, index=True)
    day = db.Column(db.String(10), nullable=False, index=True)  # YYYY-MM-DD
    scanned_at = db.Column(db.String(26), nullable=False)
    scan_clock = db.Column(db.String(8), nullable=False)  # HH:MM:SS
    session_name = db.Column(db.String(30), nullable=False, default="morning")
    status_result = db.Column(db.String(50), nullable=False)  # Present, Late, Duplicate, OutsideWindow, UnknownCard, LostCard, AccessDenied
    is_duplicate = db.Column(db.Boolean, default=False, nullable=False)
    message = db.Column(db.String(255), nullable=True)
    raw_payload = db.Column(db.Text, nullable=True)

    student = db.relationship("User", foreign_keys=[student_id])
