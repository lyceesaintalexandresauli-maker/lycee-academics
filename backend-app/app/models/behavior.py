from app.extensions import db


class BehaviorRecord(db.Model):
    """A behavior observation kept separate from attendance and discipline decisions."""

    __tablename__ = "behavior_record"
    __table_args__ = (
        db.CheckConstraint(
            "record_type IN ('Positive', 'Concern', 'Serious', 'Critical')",
            name="ck_behavior_record_type",
        ),
        db.CheckConstraint(
            "status IN ('submitted', 'under_review', 'resolved')",
            name="ck_behavior_record_status",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="RESTRICT"), nullable=False, index=True)
    student_name = db.Column(db.String(160), nullable=False)
    class_name = db.Column(db.String(100), index=True)
    department = db.Column(db.String(100))
    trade = db.Column(db.String(100))
    level = db.Column(db.String(50))
    academic_year = db.Column(db.String(9))
    reporter_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="RESTRICT"), nullable=False, index=True)
    reporter_role = db.Column(db.String(30), nullable=False)
    record_type = db.Column(db.String(20), nullable=False, index=True)
    title = db.Column(db.String(160), nullable=False)
    description = db.Column(db.Text, nullable=False)
    location = db.Column(db.String(160))
    action_taken = db.Column(db.Text)
    follow_up_required = db.Column(db.Boolean, nullable=False, default=False, server_default=db.false())
    follow_up_date = db.Column(db.String(10))
    parent_notification_required = db.Column(db.Boolean, nullable=False, default=False, server_default=db.false())
    parent_notification_status = db.Column(db.String(20), nullable=False, default="not_required", server_default="not_required")
    status = db.Column(db.String(20), nullable=False, default="submitted", server_default="submitted", index=True)
    is_published = db.Column(db.Boolean, nullable=False, default=False, server_default=db.false(), index=True)
    resolution = db.Column(db.Text)
    resolved_by_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="RESTRICT"))
    resolved_at = db.Column(db.String(19))
    created_at = db.Column(db.String(19), nullable=False, index=True)
    updated_at = db.Column(db.String(19), nullable=False)

    student = db.relationship("User", foreign_keys=[student_id])
    reporter = db.relationship("User", foreign_keys=[reporter_id])
    resolver = db.relationship("User", foreign_keys=[resolved_by_id])
