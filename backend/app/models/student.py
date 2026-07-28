from sqlalchemy import Boolean, ForeignKey, Integer, String
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

    face_model_path: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True
    )

    # Accommodation fields - admin-granted (same require_admin as the rest of this model's
    # mutations), enforced both client-side (ExamRoom skips the relevant capture/check calls
    # entirely) and server-side in face_service.py/object_detection_service.py (defense in depth -
    # a student with an accommodation must never be flagged even if a client-side bug still sends
    # a check request).
    accommodation_notes: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True
    )

    skip_face_check: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false"
    )

    skip_object_check: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false"
    )

    extra_time_minutes: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0"
    )

    user = relationship(
        "User",
        back_populates="student"
    )

    course = relationship(
        "Course",
        back_populates="students"
    )
    exam_sessions = relationship(
        "ExamSession",
        back_populates="student",
        cascade="all, delete-orphan"
    )
    roster_entries = relationship(
        "ExamRoster",
        back_populates="student",
        cascade="all, delete-orphan"
    )