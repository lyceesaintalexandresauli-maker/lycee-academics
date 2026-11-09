from app.extensions import db
class FeeTransaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    requirement_id = db.Column(db.Integer, db.ForeignKey("fee_requirement.id"))
    total_fees = db.Column(db.Float, default=150000)
    amount = db.Column(db.Float, nullable=False)
    method = db.Column(db.String(40), default="Cash")
    reference = db.Column(db.String(100))
    created_at = db.Column(db.String(19), nullable=False)
    reconciliation_status = db.Column(db.String(20), nullable=False, default="confirmed")
    reconciled_by_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    reconciled_at = db.Column(db.String(26))
    reconciliation_note = db.Column(db.Text)
    student = db.relationship("User", foreign_keys=[student_id], backref="fee_transactions")
    requirement = db.relationship("FeeRequirement", backref="payments")
    reconciled_by = db.relationship("User", foreign_keys=[reconciled_by_id])


class FeeRequirement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    title = db.Column(db.String(120), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    due_date = db.Column(db.Date, nullable=False)
    details = db.Column(db.Text)
    created_by = db.Column(db.Integer, db.ForeignKey("user.id"))
    student = db.relationship("User", foreign_keys=[student_id], backref="fee_requirements")
    creator = db.relationship("User", foreign_keys=[created_by])

