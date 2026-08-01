from fastapi import APIRouter, Depends, File, Form, UploadFile
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
from app.services.audit_log_service import AuditLogService
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
    event_type: str = Form(...),
    detail: str | None = Form(None),
    # Optional evidence screenshot - currently only sent by the Tab Monitor extension for
    # AI_TOOL_DETECTED/SEARCH_ENGINE_DETECTED (see background.js's captureEvidenceScreenshot).
    # Safe to accept as client-submitted here specifically because detection for these two event
    # types is itself entirely client-side already (the server has no independent way to know what
    # other tabs are open) - unlike FACE_LOST/PHONE_DETECTED/etc, where evidence_bytes is deliberately
    # kept off the client-facing schema because the server does its own independent detection.
    evidence: UploadFile | None = File(None),
    db: Session = Depends(get_db),
    session: ExamSession = Depends(require_session_owner_student)
):
    request = ViolationCreate(event_type=event_type, detail=detail)
    evidence_bytes = evidence.file.read() if evidence is not None else None
    return ViolationService.log_violation(session_id, request, db, evidence_bytes=evidence_bytes)


@router.get(
    "/{session_id}/violations",
    response_model=list[ViolationResponse]
)
def get_violations(
    session_id: int,
    db: Session = Depends(get_db),
    session: ExamSession = Depends(require_session_read_access),
    current_user: User = Depends(get_current_user)
):
    # Only audit staff access to another student's data - a student viewing their own
    # violations isn't the kind of access this trail exists to track.
    if current_user.role.name.lower() != "student":
        AuditLogService.log(
            current_user.id, "VIEW_VIOLATIONS", "exam_session", session_id, db,
            detail=f"student_id={session.student_id}"
        )
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
    violation: Violation = Depends(require_violation_read_access),
    current_user: User = Depends(get_current_user)
):
    if current_user.role.name.lower() != "student":
        AuditLogService.log(
            current_user.id, "VIEW_EVIDENCE", "violation", violation_id, db,
            detail=f"student_id={violation.exam_session.student_id}"
        )
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
