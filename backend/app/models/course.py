from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class Course(Base, TimestampMixin):
    __tablename__ = "courses"
    __table_args__ = (
        # Unique per-school, not globally - two different schools both having a "BSCS" course
        # code is normal, not a collision, now that a deployment can host more than one school.
        UniqueConstraint("school_id", "code", name="uq_course_school_code"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    code: Mapped[str] = mapped_column(
        String(20),
        nullable=False
    )

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )

    # Derived from the creating admin's own school (see CourseService.create), never
    # client-supplied - the multi-tenancy scoping root for all academic data (Subject/Exam/
    # Student all derive their school by joining up to this).
    school_id: Mapped[int] = mapped_column(
        ForeignKey("schools.id")
    )

    school = relationship(
        "School",
        back_populates="courses"
    )

    students = relationship(
        "Student",
        back_populates="course"
    )

    subjects = relationship(
        "Subject",
        back_populates="course"
    )