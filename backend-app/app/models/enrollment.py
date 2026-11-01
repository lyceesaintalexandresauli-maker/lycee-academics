"""Historical student enrollment linking students to the academic hierarchy."""
from datetime import datetime
from app.extensions import db


class AcademicEnrollment(db.Model):
    __tablename__ = "academic_enrollment"
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    academic_year_id = db.Column(db.Integer, db.ForeignKey("academic_year.id"), nullable=False, index=True)
    department_id = db.Column(db.Integer, db.ForeignKey("department.id"), nullable=False, index=True)
    trade_id = db.Column(db.Integer, db.ForeignKey("trade.id"), nullable=False, index=True)
    class_id = db.Column(db.Integer, db.ForeignKey("school_class.id"), nullable=False, index=True)
    status = db.Column(db.String(30), nullable=False, default="active")
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    student = db.relationship("User", backref=db.backref("academic_enrollments", lazy=True))
    academic_year = db.relationship("AcademicYear", backref=db.backref("enrollments", lazy=True))
    department = db.relationship("Department")
    trade = db.relationship("Trade")
    school_class = db.relationship("SchoolClass")
    __table_args__ = (
        db.UniqueConstraint("student_id", "academic_year_id", name="uq_enrollment_student_year"),
    )
