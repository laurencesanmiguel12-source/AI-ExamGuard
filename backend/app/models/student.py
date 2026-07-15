from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class Student(Base, TimestampMixin):
    __tablename__ = "students"

    id: Mapped[int] = mapped_column(primary_key=True)

    student_number: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        unique=True
    )

    course_id: Mapped[int] = mapped_column(
        ForeignKey("courses.id")
    )

    user = relationship(
        "User",
        back_populates="student"
    )

    course = relationship(
        "Course",
        back_populates="students"
    )