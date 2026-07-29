from sqlalchemy.orm import Session, joinedload

from app.models.audit_log import AuditLog

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
    def get_recent(db: Session):
        return (
            db.query(AuditLog)
            .options(joinedload(AuditLog.actor))
            .order_by(AuditLog.created_at.desc())
            .limit(RECENT_LIMIT)
            .all()
        )
