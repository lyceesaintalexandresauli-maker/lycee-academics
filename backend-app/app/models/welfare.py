from app.extensions import db


WELFARE_STATUSES = (
    "sick_at_school",
    "hospitalized",
    "sent_home",
    "authorized_leave",
    "welfare_concern",
    "emergency",
    "misconduct_report",
)

LOCATION_STATUSES = {"sick_at_school", "hospitalized", "sent_home", "authorized_leave"}
URGENT_STATUSES = {"hospitalized", "emergency"}
APPROVAL_STATUSES = {"hospitalized", "sent_home", "emergency"}

CASE_STATES = ("open", "follow_up", "awaiting_info", "awaiting_approval", "resolved")
APPROVAL_STATES = ("not_required", "pending", "approved", "declined")


class StudentWelfareRecord(db.Model):
    """Factual welfare case. Does not overwrite RFID attendance or issue discipline."""

    __tablename__ = "student_welfare_record"
    __table_args__ = (
        db.CheckConstraint(
            "status IN ('sick_at_school','hospitalized','sent_home','authorized_leave',"
            "'welfare_concern','emergency','misconduct_report')",
            name="ck_welfare_record_status",
        ),
        db.CheckConstraint(
            "case_state IN ('open','follow_up','awaiting_info','awaiting_approval','resolved')",
            name="ck_welfare_record_case_state",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="RESTRICT"), nullable=False, index=True)
    student_name = db.Column(db.String(160), nullable=False)
    class_name = db.Column(db.String(100), index=True)
    gender = db.Column(db.String(30))
    reporter_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="RESTRICT"), nullable=False, index=True)
    reporter_role = db.Column(db.String(30), nullable=False, index=True)
    status = db.Column(db.String(32), nullable=False, index=True)
    case_state = db.Column(db.String(24), nullable=False, default="open", server_default="open", index=True)
    details = db.Column(db.Text, nullable=False)
    authorization_by = db.Column(db.String(160))
    authorization_note = db.Column(db.Text)
    event_date = db.Column(db.String(10), nullable=False, index=True)
    expected_return_date = db.Column(db.String(10))
    actual_return_date = db.Column(db.String(10))
    follow_up_required = db.Column(db.Boolean, nullable=False, default=False, server_default=db.false())
    follow_up_date = db.Column(db.String(10), index=True)
    follow_up_notes = db.Column(db.Text)
    notify_guardian = db.Column(db.Boolean, nullable=False, default=False, server_default=db.false())
    is_urgent = db.Column(db.Boolean, nullable=False, default=False, server_default=db.false(), index=True)
    requires_admin_approval = db.Column(db.Boolean, nullable=False, default=False, server_default=db.false())
    approval_status = db.Column(db.String(20), nullable=False, default="not_required", server_default="not_required")
    approved_by_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="RESTRICT"))
    approved_at = db.Column(db.String(19))
    approval_note = db.Column(db.Text)
    info_request = db.Column(db.Text)
    info_response = db.Column(db.Text)
    assigned_to_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="RESTRICT"))
    assigned_note = db.Column(db.Text)
    reviewed_by_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="RESTRICT"))
    reviewed_at = db.Column(db.String(19))
    resolved_by_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="RESTRICT"))
    resolved_at = db.Column(db.String(19))
    resolution_note = db.Column(db.Text)
    created_at = db.Column(db.String(19), nullable=False, index=True)
    updated_at = db.Column(db.String(19), nullable=False)

    student = db.relationship("User", foreign_keys=[student_id])
    reporter = db.relationship("User", foreign_keys=[reporter_id])
    approver = db.relationship("User", foreign_keys=[approved_by_id])
    assignee = db.relationship("User", foreign_keys=[assigned_to_id])
    reviewer = db.relationship("User", foreign_keys=[reviewed_by_id])
    resolver = db.relationship("User", foreign_keys=[resolved_by_id])


class DailyWelfareReport(db.Model):
    """One submitted daily snapshot per Patron or Matron role and calendar date."""

    __tablename__ = "daily_welfare_report"
    __table_args__ = (
        db.UniqueConstraint("reporter_role", "report_date", name="uq_daily_welfare_report_role_date"),
    )

    id = db.Column(db.Integer, primary_key=True)
    reporter_role = db.Column(db.String(30), nullable=False, index=True)
    reporter_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="RESTRICT"), nullable=False, index=True)
    report_date = db.Column(db.String(10), nullable=False, index=True)
    total_students = db.Column(db.Integer, nullable=False, default=0)
    sick_count = db.Column(db.Integer, nullable=False, default=0)
    hospitalized_count = db.Column(db.Integer, nullable=False, default=0)
    sent_home_count = db.Column(db.Integer, nullable=False, default=0)
    follow_up_count = db.Column(db.Integer, nullable=False, default=0)
    incident_count = db.Column(db.Integer, nullable=False, default=0)
    observations = db.Column(db.Text, nullable=False)
    recommended_actions = db.Column(db.Text)
    serious_incidents = db.Column(db.Text)
    submitted_at = db.Column(db.String(19), nullable=False)
    reviewed_by_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="RESTRICT"))
    reviewed_at = db.Column(db.String(19))
    review_comments = db.Column(db.Text)

    reporter = db.relationship("User", foreign_keys=[reporter_id])
    reviewer = db.relationship("User", foreign_keys=[reviewed_by_id])


class WelfareAuditEvent(db.Model):
    """Immutable trail of welfare case and report actions."""

    __tablename__ = "welfare_audit_event"

    id = db.Column(db.Integer, primary_key=True)
    actor_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="RESTRICT"), nullable=False, index=True)
    actor_name = db.Column(db.String(160), nullable=False)
    action = db.Column(db.String(80), nullable=False, index=True)
    student_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="RESTRICT"), index=True)
    record_id = db.Column(db.Integer, db.ForeignKey("student_welfare_record.id", ondelete="RESTRICT"), index=True)
    report_id = db.Column(db.Integer, db.ForeignKey("daily_welfare_report.id", ondelete="RESTRICT"), index=True)
    before_state = db.Column(db.String(80))
    after_state = db.Column(db.String(80))
    reason = db.Column(db.Text)
    created_at = db.Column(db.String(19), nullable=False, index=True)

    actor = db.relationship("User", foreign_keys=[actor_id])
    student = db.relationship("User", foreign_keys=[student_id])
    record = db.relationship("StudentWelfareRecord", foreign_keys=[record_id])
    report = db.relationship("DailyWelfareReport", foreign_keys=[report_id])
