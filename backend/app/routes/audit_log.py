from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import effective_school_id, require_admin
from app.core.database import get_db
from app.models.user import User
from app.schemas.audit_log import AuditLogResponse
from app.services.audit_log_service import AuditLogService

router = APIRouter(
    prefix="/admin",
    tags=["Admin"]
)


@router.get(
    "/audit-log",
    response_model=list[AuditLogResponse]
)
def get_audit_log(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    return AuditLogService.get_recent(db, effective_school_id(current_user))
