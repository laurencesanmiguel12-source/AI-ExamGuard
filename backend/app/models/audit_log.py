from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class AuditLog(Base, TimestampMixin):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True)

    actor_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id")
    )

    # e.g. "VIEW_VIOLATIONS", "VIEW_EVIDENCE", "UPDATE_ACCOMMODATION" - deliberately scoped to
    # staff access/changes to sensitive student proctoring data, not a generic "every GET request"
    # log (that would be noisy and log routine list views nobody needs to audit).
    action: Mapped[str] = mapped_column(
        String(50),
        nullable=False
    )

    resource_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False
    )

    resource_id: Mapped[int] = mapped_column(
        Integer,
        nullable=False
    )

    detail: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True
    )

    actor = relationship("User")

    @property
    def actor_email(self) -> str:
        return self.actor.email if self.actor else f"user #{self.actor_user_id}"
