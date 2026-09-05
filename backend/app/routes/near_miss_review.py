import os

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.auth.dependencies import effective_school_id, require_admin
from app.core.database import get_db
from app.models.user import User
from app.schemas.near_miss_capture import (
    NearMissCandidate,
    NearMissResponse,
    NearMissReviewRequest,
)
from app.services.audit_log_service import AuditLogService
from app.services.near_miss_capture_service import NearMissCaptureService

# Admin-only, and school-scoped inside the service - the same footing as the violation training
# review queue this sits beside.
router = APIRouter(
    prefix="/admin/near-miss-review",
    tags=["Admin"]
)


@router.get("/pending", response_model=list[NearMissCandidate])
def list_pending(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    return NearMissCaptureService.list_pending(db, effective_school_id(current_user))


# Declared before /{capture_id} so the literal path is not swallowed by the param route - the
# ordering rule this codebase has been bitten by before (see CLAUDE.md).
@router.get("/{capture_id}/evidence")
def get_evidence(
    capture_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    capture = NearMissCaptureService.get_for_school(
        capture_id, db, effective_school_id(current_user)
    )
    if not capture.evidence_path or not os.path.exists(capture.evidence_path):
        raise HTTPException(status_code=404, detail="Evidence image not found.")

    # Logged for the same reason viewing violation evidence is: someone looked at a webcam frame
    # of a student, and that should be attributable even though no violation was recorded.
    AuditLogService.log(
        current_user.id, "VIEW_NEAR_MISS_EVIDENCE", "near_miss_capture", capture_id, db
    )
    return FileResponse(capture.evidence_path, media_type="image/jpeg")


@router.put("/{capture_id}", response_model=NearMissResponse)
def review(
    capture_id: int,
    request: NearMissReviewRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    return NearMissCaptureService.review(
        capture_id, request.decision, current_user.id, db, effective_school_id(current_user)
    )
