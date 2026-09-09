from datetime import date

from sqlalchemy import Date, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

# PLANNED  - being set up. Sections and enrolment can be built; no exam may be sat.
# ACTIVE   - running. The default scope for every "current" view in the app.
# CLOSED   - finished. Read-only history: no new exams, no new enrolment, no new attempts.
#
# A real state machine rather than a date comparison, because "is this term over" is an
# administrative decision, not an arithmetic one - marking finished early, or holding a term open
# for a late makeup exam, are both normal and neither is expressible with dates alone.
TERM_STATUSES = ("PLANNED", "ACTIVE", "CLOSED")

# The only transitions allowed. Reopening a CLOSED term is deliberately permitted (back to
# ACTIVE): a term closed by mistake, or reopened for a deferred sitting, is a real situation, and
# refusing it would push people to edit the database by hand.
TERM_TRANSITIONS = {
    "PLANNED": {"ACTIVE"},
    "ACTIVE": {"CLOSED"},
    "CLOSED": {"ACTIVE"},
}


class Term(Base, TimestampMixin):
    """One semester or summer session inside an academic year."""

    __tablename__ = "terms"
    __table_args__ = (
        UniqueConstraint("academic_year_id", "sequence", name="uq_term_year_sequence"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    academic_year_id: Mapped[int] = mapped_column(
        ForeignKey("academic_years.id"),
        nullable=False
    )

    # "1st Semester", "2nd Semester", "Summer" - naming varies by institution, so it is not an enum.
    name: Mapped[str] = mapped_column(String(50), nullable=False)

    # Ordering within the year. Explicit rather than inferred from dates, because a summer term
    # may overlap or abut the semesters around it depending on the institution.
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)

    starts_on: Mapped[date] = mapped_column(Date, nullable=False)
    ends_on: Mapped[date] = mapped_column(Date, nullable=False)

    status: Mapped[str] = mapped_column(
        String(20),
        default="PLANNED",
        nullable=False
    )

    academic_year = relationship("AcademicYear", back_populates="terms")
    sections = relationship(
        "Section",
        back_populates="term",
        cascade="all, delete-orphan"
    )
