from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import require_admin
from app.core.database import get_db
from app.models.user import User
from app.services.retention_service import RetentionService

router = APIRouter(
    prefix="/admin/retention",
    tags=["Admin"]
)


@router.get("/preview")
def preview_purge(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    return RetentionService.preview_purge(db)


@router.post("/purge")
def purge_expired_evidence(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    purged = RetentionService.purge_expired_evidence(db, current_user.id)
    return {"purged_count": purged}
