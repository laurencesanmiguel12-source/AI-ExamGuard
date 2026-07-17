from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class Instructor(Base, TimestampMixin):
    __tablename__ = "instructors"

    id: Mapped[int] = mapped_column(primary_key=True)

    employee_number: Mapped[str] = mapped_column(
        String(50),
        unique=True,
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