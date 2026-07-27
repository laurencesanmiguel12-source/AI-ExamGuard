from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import require_instructor
from app.auth.session_access import require_session_owner_student, require_session_read_access
from app.core.database import get_db
from app.models.exam_session import ExamSession
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
    db: Session = Depends(get_db),
    session: ExamSession = Depends(require_session_owner_student)
):
    return ViolationService.log_violation(session_id, request, db)


@router.get(
    "/{session_id}/violations",
    response_model=list[ViolationResponse]
)
def get_violations(
    session_id: int,
    db: Session = Depends(get_db),
    session: ExamSession = Depends(require_session_read_access)
):
    return ViolationService.get_violations(session_id, db)


@router.get(
    "/{session_id}/risk"
)
def get_risk(
    session_id: int,
    db: Session = Depends(get_db),
    session: ExamSession = Depends(require_session_read_access)
):
    return {"risk_score": RiskService.compute_risk(session_id, db)}
