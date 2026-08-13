from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import require_admin
from app.core.database import get_db
from app.models.user import User
from app.schemas.violation import (
    TrainingReviewCandidate,
    TrainingReviewRequest,
    ViolationResponse,
)
from app.services.training_review_service import TrainingReviewService

router = APIRouter(
    prefix="/admin/training-review",
    tags=["Admin"]
)


@router.get("/pending", response_model=list[TrainingReviewCandidate])
def list_pending(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    return TrainingReviewService.list_pending(db, current_user.school_id)


@router.put("/{violation_id}", response_model=ViolationResponse)
def review(
    violation_id: int,
    request: TrainingReviewRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    return TrainingReviewService.review(
        violation_id, request.decision, current_user.id, db
    )
