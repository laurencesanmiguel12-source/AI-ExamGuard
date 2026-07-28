from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import require_admin
from app.core.database import get_db
from app.models.user import User
from app.schemas.system import SystemStatus
from app.services.system_status_service import SystemStatusService

router = APIRouter(
    prefix="/admin",
    tags=["Admin"]
)


@router.get(
    "/system-status",
    response_model=SystemStatus
)
def get_system_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    return SystemStatusService.get_status(db)
