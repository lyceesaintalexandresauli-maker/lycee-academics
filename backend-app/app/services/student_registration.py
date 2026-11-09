"""Student account creation flows shared by registration routes."""
from datetime import date

from app.extensions import db
from app.models import AcademicEnrollment, AcademicYear, Department, SchoolClass, StudentGuardian, Trade, User
from app.utils.helpers import generate_sdms_code, now_string


def create_manual_student(fields, actor, parent=None):
    """Create a student and relational class enrollment without an RFID card."""
    school_class = SchoolClass.query.join(Trade).join(Department).filter(
        db.func.lower(SchoolClass.name) == fields["class_name"].casefold(),
        db.func.lower(SchoolClass.level) == fields["level"].casefold(),
        db.func.lower(Trade.name) == fields["trade"].casefold(),
        db.func.lower(Department.name) == fields["department"].casefold(),
        SchoolClass.is_active.is_(True), Trade.is_active.is_(True), Department.is_active.is_(True),
    ).first()
    if not school_class:
        raise ValueError("The selected class is not present in the active school structure.")

    # Use the persisted class hierarchy as the source of truth for each student.
    department = school_class.trade.department
    trade = school_class.trade

    academic_year = AcademicYear.query.filter_by(name=fields["academic_year"]).first()
    if not academic_year:
        academic_year = AcademicYear(
            name=fields["academic_year"],
            is_current=AcademicYear.query.filter_by(is_current=True).first() is None,
        )
        db.session.add(academic_year)
        db.session.flush()

    student = User(
        username=fields["username"],
        full_name=fields["full_name"],
        role="student",
        class_name=school_class.name,
        department=department.name,
        trade=trade.name,
        level=school_class.level,
        sdms_code=generate_sdms_code(),
        date_of_birth=fields["date_of_birth"],
        gender=fields["gender"],
        academic_year=fields["academic_year"],
        guardian_name=fields["guardian_name"],
        guardian_relationship=fields["guardian_relationship"],
        guardian_phone=fields["guardian_phone"],
        address=fields["address"],
        parent_id=parent.id if parent else None,
        rfid_uid=None,
        is_active_account=True,
    )
    student.set_password(fields["password"])
    db.session.add(student)
    db.session.flush()
    db.session.add(AcademicEnrollment(
        student_id=student.id,
        academic_year_id=academic_year.id,
        department_id=department.id,
        trade_id=school_class.trade_id,
        class_id=school_class.id,
        status="active",
        start_date=date.today(),
    ))
    if parent:
        db.session.add(StudentGuardian(
            student_id=student.id,
            guardian_id=parent.id,
            relationship=fields["guardian_relationship"],
            status="verified",
            verified_by_id=actor.id,
            verified_at=now_string(),
        ))
    return student
