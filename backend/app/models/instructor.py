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
    # Named relationship rather than querying InstructorSubject ad hoc, so the response schema can
    # walk instructor -> subject -> course in one place.
    subject_links = relationship(
        "InstructorSubject",
        viewonly=True
    )

    @property
    def instructor_name(self) -> str | None:
        """Mirrors Student.student_name.

        The defense panel reported that the instructor list showed no name at all, and the cause
        was here: nothing on this model or its response schema ever exposed one, so the table
        could only print a raw user_id. Students already had this; instructors did not.
        """
        if self.user is None:
            return None
        return f"{self.user.first_name} {self.user.last_name}"

    @property
    def email(self) -> str | None:
        return self.user.email if self.user is not None else None

    # The two halves as stored, not split back out of instructor_name. A display name cannot be
    # taken apart reliably - "Ana Maria Cruz" splits into the wrong halves - and an edit form that
    # guesses them writes the guess back on save.
    @property
    def first_name(self) -> str | None:
        return self.user.first_name if self.user is not None else None

    @property
    def last_name(self) -> str | None:
        return self.user.last_name if self.user is not None else None

    @property
    def assignments(self) -> list[dict]:
        """What this instructor actually teaches, subject AND course together.

        The panel's second point: two instructors assigned to the same subject were
        indistinguishable, because the list showed subjects with no course context. A subject code
        alone is ambiguous across courses, so both are carried here.
        """
        out = []
        for link in self.subject_links:
            subject = link.subject
            if subject is None:
                continue
            course = subject.course
            out.append({
                "subject_id": subject.id,
                "subject_code": subject.code,
                "subject_name": subject.name,
                "course_id": course.id if course is not None else None,
                "course_code": course.code if course is not None else None,
                "course_name": course.name if course is not None else None,
            })
        return sorted(out, key=lambda a: (a["course_code"] or "", a["subject_code"] or ""))