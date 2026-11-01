from app.extensions import db


class Attendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    day = db.Column(db.String(10), nullable=False, index=True)
    status = db.Column(db.String(30), nullable=False, default="Present")
    arrival_time = db.Column(db.String(26))
    afternoon_time = db.Column(db.String(26))
    source = db.Column(db.String(30), default="RFID")
    note = db.Column(db.String(500))
    edited_by = db.Column(db.Integer, db.ForeignKey("user.id"))

    # Authoritative RFID physical attendance extensions
    session_name = db.Column(db.String(30), default="morning")
    device_id = db.Column(db.String(64), nullable=True)
    card_uid = db.Column(db.String(100), nullable=True)
    is_corrected = db.Column(db.Boolean, default=False, nullable=False)
    correction_reason = db.Column(db.Text, nullable=True)
    corrected_at = db.Column(db.String(26), nullable=True)
    explanation = db.Column(db.Text, nullable=True)  # For Explained Absence
    explanation_approved_by = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)

    student = db.relationship("User", foreign_keys=[student_id], backref="attendance_records")
    editor = db.relationship("User", foreign_keys=[edited_by])
    explanation_approver = db.relationship("User", foreign_keys=[explanation_approved_by])


class AttendanceAuditTrail(db.Model):
    """Immutable audit trail for all attendance status changes, corrections, and excuses."""
    id = db.Column(db.Integer, primary_key=True)
    attendance_id = db.Column(db.Integer, db.ForeignKey("attendance.id"), nullable=False, index=True)
    student_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    day = db.Column(db.String(10), nullable=False, index=True)
    session_name = db.Column(db.String(30), default="morning")
    old_status = db.Column(db.String(30), nullable=True)
    new_status = db.Column(db.String(30), nullable=False)
    old_source = db.Column(db.String(30), nullable=True)
    new_source = db.Column(db.String(30), nullable=False)
    changed_by_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    changed_at = db.Column(db.String(26), nullable=False)
    reason = db.Column(db.Text, nullable=False)
    ip_address = db.Column(db.String(45), nullable=True)

    student = db.relationship("User", foreign_keys=[student_id])
    changer = db.relationship("User", foreign_keys=[changed_by_id])
    attendance = db.relationship("Attendance", foreign_keys=[attendance_id], backref="audit_trails")
