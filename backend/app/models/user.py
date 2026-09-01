from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)

    # Email is the only account identifier - there is deliberately no username column. See
    # AuthService.create_user_account for the registration failure dropping it fixed.
    email: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False
    )

    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )
    first_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )

    last_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True
    )

    last_login: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    role_id: Mapped[int] = mapped_column(
        ForeignKey("roles.id")
    )

    # Every account - admin, instructor, student - belongs to exactly one school. This is the
    # primary multi-tenancy scoping key for people; Course carries the equivalent key for academic
    # data (see Course.school_id) since everything else (Subject/Exam/Student-via-course/
    # Instructor-via-InstructorSubject) is derivable by joining up to one of those two.
    school_id: Mapped[int] = mapped_column(
        ForeignKey("schools.id")
    )

    role = relationship(
        "Role",
        back_populates="users"
    )

    school = relationship(
        "School",
        back_populates="users"
    )

    student = relationship(
        "Student",
        back_populates="user",
        uselist=False
    )

    instructor = relationship(
        "Instructor",
        back_populates="user",
        uselist=False
    )