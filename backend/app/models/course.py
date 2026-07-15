from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class Course(Base, TimestampMixin):
    __tablename__ = "courses"

    id: Mapped[int] = mapped_column(primary_key=True)

    code: Mapped[str] = mapped_column(
        String(20),
        unique=True,
        nullable=False
    )

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )

    students = relationship(
        "Student",
        back_populates="course"
    )

    subjects = relationship(
        "Subject",
        back_populates="course"
    )