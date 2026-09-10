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

    @property
    def student_name(self) -> str | None:
        if self.user is None:
            return None
        return f"{self.user.first_name} {self.user.last_name}"

    @property
    def email(self) -> str | None:
        """Their sign-in address, read through the linked account.

        Surfaced for the same reason InstructorResponse carries one: the edit form has to show the
        current address before it can offer to correct it, and a form that opens with a blank
        required field submits a change nobody asked for.
        """
        return self.user.email if self.user is not None else None

    # The two halves as stored, not split back out of student_name. A display name cannot be
    # taken apart reliably - "Ana Maria Cruz" splits into the wrong halves - and an edit form that
    # guesses them writes the guess back on save.
    @property
    def first_name(self) -> str | None:
        return self.user.first_name if self.user is not None else None

    @property
    def last_name(self) -> str | None:
        return self.user.last_name if self.user is not None else None