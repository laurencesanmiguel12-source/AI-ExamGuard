from sqlalchemy.orm import Session, joinedload

from app.models.audit_log import AuditLog
from app.models.user import User

RECENT_LIMIT = 200


class AuditLogService:

    @staticmethod
    def log(
        actor_user_id: int,
        action: str,
        resource_type: str,
        resource_id: int,
        db: Session,
        detail: str | None = None
    ):
        entry = AuditLog(
            actor_user_id=actor_user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            detail=detail
        )
        db.add(entry)
        db.commit()

    @staticmethod
    def get_recent(db: Session, school_id: int | None):
        # Scoped by the acting user's own school - previously system-wide, so School A's admin
        # could read School B's entire audit trail (who viewed what evidence, when).
        # school_id=None is the one deliberate exception: a super admin gets the platform-wide
        # trail, each entry still shows its own actor so it's not actually ambiguous which
        # school an action belongs to the way an aggregated stat would be.
        query = (
            db.query(AuditLog)
            .join(User, AuditLog.actor_user_id == User.id)
            .options(joinedload(AuditLog.actor))
        )
        if school_id is not None:
            query = query.filter(User.school_id == school_id)
        return query.order_by(AuditLog.created_at.desc()).limit(RECENT_LIMIT).all()
