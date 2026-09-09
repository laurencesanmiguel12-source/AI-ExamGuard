from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship


from app.models.base import Base, TimestampMixin



class Exam(Base, TimestampMixin):
    __tablename__ = "exams"

    id: Mapped[int] = mapped_column(primary_key=True)

    title: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    duration_minutes: Mapped[int] = mapped_column(
        Integer,
        nullable=False
    )

    total_points: Mapped[int] = mapped_column(
        Integer,
        default=0
    )
    passing_score: Mapped[int] = mapped_column(
        nullable=False
    )

    # Null means the retake-flagging feature is off for this exam - no threshold to breach.
    max_risk_score: Mapped[int | None] = mapped_column(
        nullable=True
    )

    start_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True)
    )

    end_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True)
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=False
    )

    subject_id: Mapped[int] = mapped_column(
        ForeignKey("subjects.id")
    )

    instructor_id: Mapped[int] = mapped_column(
        ForeignKey("instructors.id")
    )

    # The exam's real home. A Subject is a catalogue entry with no time dimension, no class list
    # and no single teacher, so hanging an exam off one left nowhere for a school year to attach,
    # no way to tell two instructors of the same subject apart, and no roster to inherit.
    #
    # Nullable through steps 3-4 of the migration: every existing exam has been backfilled, but
    # subject_id and instructor_id remain authoritative until step 5 retires them, so old code
    # paths keep working while new ones read through here.
    section_id: Mapped[int | None] = mapped_column(
        ForeignKey("sections.id"),
        nullable=True
    )

    subject = relationship(
        "Subject",
        back_populates="exams"
    )

    instructor = relationship(
        "Instructor",
        back_populates="exams"
    )

    questions = relationship(
        "Question",
        back_populates="exam",
        cascade="all, delete-orphan"
    )
    exam_sessions = relationship(
        "ExamSession",
        back_populates="exam",
        cascade="all, delete-orphan"
    )
    roster_entries = relationship(
        "ExamRoster",
        back_populates="exam",
        cascade="all, delete-orphan"
    )
    section = relationship("Section")

    # --- reached through the section ---------------------------------------------------------
    # This is the entire point of step 3: term and academic year stop being fields anyone fills
    # in on an exam form and become facts you arrive at by following one link. All three degrade
    # to None on an exam with no section yet, so nothing breaks mid-migration.

    @property
    def term(self):
        return self.section.term if self.section is not None else None

    @property
    def academic_year(self):
        term = self.term
        return term.academic_year if term is not None else None

    @property
    def term_label(self) -> str | None:
        """"1st Semester 2026-2027" - how a term reads on screen."""
        term = self.term
        if term is None:
            return None
        year = term.academic_year
        return f"{term.name} {year.label}" if year is not None else term.name