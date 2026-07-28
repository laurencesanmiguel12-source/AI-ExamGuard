from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, require_instructor
from app.auth.session_access import (
    require_session_owner_student,
    require_session_read_access,
    require_violation_manage_access,
    require_violation_owner_student,
    require_violation_read_access,
)
from app.core.database import get_db
from app.models.exam_session import ExamSession
from app.models.user import User
from app.models.violation import Violation
from app.schemas.violation import (
    LiveMonitorResponse,
    RiskSummaryResponse,
    ViolationAppealRequest,
    ViolationAppealReviewRequest,
    ViolationCreate,
    ViolationResponse,
)
from app.services.risk_service import RiskService
from app.services.violation_service import ViolationService

router = APIRouter(
    prefix="/exam-sessions",
    tags=["Violations"]
)

violations_router = APIRouter(
    prefix="/violations",
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


@router.get(
    "/{session_id}/risk-summary",
    response_model=RiskSummaryResponse
)
def get_risk_summary(
    db: Session = Depends(get_db),
    session: ExamSession = Depends(require_session_read_access)
):
    return RiskService.get_session_summary(session, db)


@violations_router.get(
    "/{violation_id}/evidence"
)
def get_evidence(
    violation_id: int,
    db: Session = Depends(get_db),
    violation: Violation = Depends(require_violation_read_access)
):
    path = ViolationService.get_evidence_path(violation_id, db)
    return FileResponse(path, media_type="image/jpeg")


@violations_router.post(
    "/{violation_id}/appeal",
    response_model=ViolationResponse
)
def file_appeal(
    violation_id: int,
    request: ViolationAppealRequest,
    db: Session = Depends(get_db),
    violation: Violation = Depends(require_violation_owner_student)
):
    return ViolationService.file_appeal(violation_id, request.reason, db)


@violations_router.put(
    "/{violation_id}/appeal-review",
    response_model=ViolationResponse
)
def review_appeal(
    violation_id: int,
    request: ViolationAppealReviewRequest,
    db: Session = Depends(get_db),
    violation: Violation = Depends(require_violation_manage_access),
    current_user: User = Depends(get_current_user)
):
    return ViolationService.review_appeal(
        violation_id, request.status, request.response, current_user.id, db
    )
