from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

SCHOOL_PENDING = "pending"
SCHOOL_APPROVED = "approved"
SCHOOL_REJECTED = "rejected"

# Only an approved school can be logged into or picked on the public student-registration form.
SCHOOL_STATUSES = (SCHOOL_PENDING, SCHOOL_APPROVED, SCHOOL_REJECTED)


class School(Base, TimestampMixin):
    __tablename__ = "schools"

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

    slug: Mapped[str] = mapped_column(
        String(150),
        unique=True,
        nullable=False
    )

    # Deactivating (super admin only) blocks login for every one of this school's users without
    # deleting their data - see auth/service.py's login check.
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true"
    )

    # Deliberately separate from is_active rather than reusing it: "never reviewed yet" and
    # "reviewed, approved, later suspended" are different states that need different messages at
    # the login screen, and collapsing them would make an un-reviewed school indistinguishable
    # from one a super admin deliberately shut off. Self-service signup creates schools as
    # "pending"; every school that existed before this column did is backfilled to "approved".
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=SCHOOL_PENDING,
        server_default=SCHOOL_APPROVED  # only applies to rows already there at migration time
    )

    # Shown to the applicant on the login screen when rejected, so a rejection is actionable
    # rather than a dead end. Also set on approval when the reviewer leaves a note.
    review_note: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True
    )

    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    # use_alter + an explicit name are load-bearing, not decoration: users.school_id already
    # points at schools, so this column closes a circular FK dependency between the two tables.
    # Alembic is unaffected (it ADDs the constraint after both tables exist), but the test suite
    # builds its schema with Base.metadata.create_all/drop_all, which topologically sorts tables
    # and raises CircularDependencyError unless this constraint is emitted as its own
    # ALTER TABLE afterwards.
    reviewed_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", use_alter=True, name="fk_schools_reviewed_by_user_id"),
        nullable=True
    )

    # See User.school - reviewed_by_user_id makes the FK path between schools and users
    # ambiguous, so both sides have to name the column they join on.
    users = relationship(
        "User",
        back_populates="school",
        foreign_keys="User.school_id"
    )

    reviewed_by = relationship(
        "User",
        foreign_keys=[reviewed_by_user_id]
    )

    courses = relationship(
        "Course",
        back_populates="school"
    )
