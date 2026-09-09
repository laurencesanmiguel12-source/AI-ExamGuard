from datetime import date

from sqlalchemy import Boolean, Date, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class AcademicYear(Base, TimestampMixin):
    """One school year, e.g. "2026-2027".

    The top of the academic hierarchy the defense panel asked for. Nothing in this codebase had
    any concept of when something happened beyond a raw timestamp, so last year's exams and this
    year's sat in one undifferentiated pile with no way to scope, archive or roll over.
    """

    __tablename__ = "academic_years"
    __table_args__ = (
        # Two schools may both run "2026-2027"; one school may not define it twice.
        UniqueConstraint("school_id", "label", name="uq_academic_year_school_label"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    school_id: Mapped[int] = mapped_column(
        ForeignKey("schools.id"),
        nullable=False
    )

    # Free text rather than a start/end year pair: institutions write this differently
    # ("2026-2027", "AY 2026-27", "SY 2026-2027") and it is a label, not something to compute on.
    label: Mapped[str] = mapped_column(
        String(50),
        nullable=False
    )

    starts_on: Mapped[date] = mapped_column(Date, nullable=False)
    ends_on: Mapped[date] = mapped_column(Date, nullable=False)

    # Exactly one per school, enforced in the service layer rather than by a constraint (a partial
    # unique index would work on Postgres but not in the SQLite-backed tooling used elsewhere).
    # This is what lets every list in the app default to "the current year" instead of making
    # somebody pick one on every single form.
    is_current: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False
    )

    school = relationship("School")
    terms = relationship(
        "Term",
        back_populates="academic_year",
        cascade="all, delete-orphan",
        order_by="Term.sequence"
    )
