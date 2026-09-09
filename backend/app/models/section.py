from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class Section(Base, TimestampMixin):
    """One offering of one subject, in one term, taught by one instructor.

    The hinge of the whole academic hierarchy, and the entity whose absence caused every symptom
    the defense panel reported.

    A Subject is a CATALOGUE entry - "CS-101, Programming 1" - a permanent fact about the
    curriculum with no time dimension, no class list and no single teacher. Exams were hung
    directly off it, which is why there was nowhere for a school year or semester to attach, why
    two instructors assigned the same subject were indistinguishable, and why every exam roster
    had to be assembled by hand: no entity represented a class, so there was no class list to
    inherit.

    A Section carries all four facts at once - subject, term, instructor, enrolled group - so an
    exam that points here reaches every one of them through a single link.
    """

    __tablename__ = "sections"
    __table_args__ = (
        # "CS-101 Section A" may exist once per term, and again next term.
        UniqueConstraint("subject_id", "term_id", "code", name="uq_section_subject_term_code"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    subject_id: Mapped[int] = mapped_column(ForeignKey("subjects.id"), nullable=False)
    term_id: Mapped[int] = mapped_column(ForeignKey("terms.id"), nullable=False)

    # One owning instructor, not a many-to-many. This is the fact the permission layer already
    # assumes - require_exam_owner, roster access, the retake decision all behave as though an
    # instructor owns a class - but which the data model could not previously express, so access
    # had to be approximated through subject assignment.
    instructor_id: Mapped[int] = mapped_column(ForeignKey("instructors.id"), nullable=False)

    # "A", "B", "1", "BSCS-2A" - the label that distinguishes two offerings of one subject.
    code: Mapped[str] = mapped_column(String(20), nullable=False)

    # Advisory only: enrolment is not blocked by it. A hard cap belongs to a registrar's system,
    # and refusing a legitimate late enrolment on exam week would be worse than a full class.
    capacity: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Free text ("MWF 9:00-10:00, Rm 302"). Deliberately not structured - timetabling, room
    # allocation and clash detection are explicitly out of scope for an examination platform.
    schedule: Mapped[str | None] = mapped_column(String(200), nullable=True)

    subject = relationship("Subject")
    term = relationship("Term", back_populates="sections")
    instructor = relationship("Instructor")
    enrollments = relationship(
        "Enrollment",
        back_populates="section",
        cascade="all, delete-orphan"
    )

    @property
    def label(self) -> str:
        """How a section reads on screen: "CS-101 A"."""
        subject_code = self.subject.code if self.subject is not None else "?"
        return f"{subject_code} {self.code}"
