from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import require_instructor
from app.core.database import get_db
from app.models.user import User
from app.schemas.violation import (
    LiveMonitorResponse,
    ViolationCreate,
    ViolationResponse,
)
from app.services.risk_service import RiskService
from app.services.violation_service import ViolationService

router = APIRouter(
    prefix="/exam-sessions",
    tags=["Violations"]
)


@router.get(
    "/live",
    response_model=LiveMonitorResponse
)
def get_live_sessions(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_instructor)
):
    return RiskService.get_live_sessions(db)


@router.post(
    "/{session_id}/violations",
    response_model=ViolationResponse
)
def log_violation(
    session_id: int,
    request: ViolationCreate,
    db: Session = Depends(get_db)
):
    return ViolationService.log_violation(session_id, request, db)


@router.get(
    "/{session_id}/violations",
    response_model=list[ViolationResponse]
)
def get_violations(
    session_id: int,
    db: Session = Depends(get_db)
):
    return ViolationService.get_violations(session_id, db)


@router.get(
    "/{session_id}/risk"
)
def get_risk(
    session_id: int,
    db: Session = Depends(get_db)
):
    return {"risk_score": RiskService.compute_risk(session_id, db)}
