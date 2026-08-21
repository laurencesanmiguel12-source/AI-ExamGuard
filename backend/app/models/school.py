from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


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

    users = relationship(
        "User",
        back_populates="school"
    )

    courses = relationship(
        "Course",
        back_populates="school"
    )
