from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class Instructor(Base, TimestampMixin):
    __tablename__ = "instructors"

    id: Mapped[int] = mapped_column(primary_key=True)

    # Not globally unique - two different schools independently numbering their own staff (e.g.
    # both using "EMP-001") is harmless, since nothing looks an Instructor up by employee_number
    # (it's a display label, not a key). Uniqueness is instead enforced per-school at the service
    # layer (see InstructorService.create).
    employee_number: Mapped[str] = mapped_column(
        String(50),
        nullable=False
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        unique=True
    )

    user = relationship(
        "User",
        back_populates="instructor"
    )
    exams = relationship(
        "Exam",
        back_populates="instructor"
    )