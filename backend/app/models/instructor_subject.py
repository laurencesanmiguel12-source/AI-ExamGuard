from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class InstructorSubject(Base, TimestampMixin):
    __tablename__ = "instructor_subjects"
    __table_args__ = (
        UniqueConstraint("instructor_id", "subject_id", name="uq_instructor_subject"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    instructor_id: Mapped[int] = mapped_column(
        ForeignKey("instructors.id")
    )

    subject_id: Mapped[int] = mapped_column(
        ForeignKey("subjects.id")
    )

    instructor = relationship("Instructor")
    subject = relationship("Subject")
