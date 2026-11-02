"""Remove class_section and desired_section columns; remove section from school_class."""

from sqlalchemy import inspect, text


def upgrade(connection):
    inspector = inspect(connection)

    if inspector.has_table("user"):
        user_columns = {column["name"] for column in inspector.get_columns("user")}
        if "class_section" in user_columns:
            connection.execute(text('ALTER TABLE "user" DROP COLUMN "class_section"'))

    if inspector.has_table("admission_applicant"):
        applicant_columns = {
            column["name"] for column in inspector.get_columns("admission_applicant")
        }
        if "desired_section" in applicant_columns:
            connection.execute(
                text('ALTER TABLE "admission_applicant" DROP COLUMN "desired_section"')
            )

    if inspector.has_table("school_class"):
        class_columns = {column["name"] for column in inspector.get_columns("school_class")}
        if "section" in class_columns:
            connection.execute(text('ALTER TABLE "school_class" DROP COLUMN "section"'))
