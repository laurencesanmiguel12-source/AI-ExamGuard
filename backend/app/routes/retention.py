from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import effective_school_id, is_super_admin, require_admin
from app.core.database import get_db
from app.models.user import User
from app.services.retention_service import RetentionService

router = APIRouter(
    prefix="/admin/retention",
    tags=["Admin"]
)


@router.get("/preview")
def preview_purge(
    school_id: int | None = Query(None, description="Super admin only - preview one specific school instead of every school"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    # A super admin previewing with no school_id sees every school combined - read-only, so
    # unlike purge below there's no accidental-blast-radius risk in letting that be the default.
    target = school_id if (school_id is not None and is_super_admin(current_user)) else effective_school_id(current_user)
    return RetentionService.preview_purge(db, target)


@router.post("/purge")
def purge_expired_evidence(
    school_id: int | None = Query(None, description="Required for a super admin - which school to purge. Ignored for a regular admin, who always purges their own."),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    if is_super_admin(current_user):
        if school_id is None:
            raise HTTPException(
                status_code=400,
                detail="school_id is required to purge as a super admin - this deletes evidence files, so it's never implicitly platform-wide."
            )
        target = school_id
    else:
        target = current_user.school_id

    purged = RetentionService.purge_expired_evidence(db, current_user.id, target)
    return {"purged_count": purged}
