from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

# ENROLLED  - currently taking it. These are the students an exam roster inherits.
# DROPPED   - left the section. Excluded from future rosters, but the row is kept rather than
#             deleted so their existing attempts and violations keep a coherent context.
# COMPLETED - the term closed with them still enrolled. Historical, not current.
ENROLLMENT_STATUSES = ("ENROLLED", "DROPPED", "COMPLETED")

# The one status that means "this person is in this class right now".
ACTIVE_ENROLLMENT = "ENROLLED"


class Enrollment(Base, TimestampMixin):
    """One student in one section - the class list.

    student.course_id says "is a BSCS student", which is a programme, not a timetable. Nothing
    recorded what a student was actually TAKING in a given term, so every exam roster had to be
    assembled by hand from scratch. This is the missing fact.
    """

    __tablename__ = "enrollments"
    __table_args__ = (
        UniqueConstraint("section_id", "student_id", name="uq_enrollment_section_student"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    section_id: Mapped[int] = mapped_column(ForeignKey("sections.id"), nullable=False)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), nullable=False)

    status: Mapped[str] = mapped_column(
        String(20),
        default=ACTIVE_ENROLLMENT,
        nullable=False
    )

    enrolled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    section = relationship("Section", back_populates="enrollments")
    student = relationship("Student")
