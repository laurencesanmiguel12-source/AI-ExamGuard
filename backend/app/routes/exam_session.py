from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.auth.session_access import (
    require_session_manage_access,
    require_session_owner_student,
    require_session_read_access,
)
from app.auth.student_context import get_current_student
from app.core.database import get_db
from app.models.exam_session import ExamSession
from app.models.student import Student
from app.models.user import User
from app.schemas.exam_session import (
    ExamSessionCreate,
    ExamSessionResponse,
    ExamSessionUpdate,
    RetakeReviewRequest,
)
from app.services.exam_session_service import ExamSessionService

router = APIRouter(
    prefix="/exam-sessions",
    tags=["Exam Sessions"]
)


@router.post(
    "/start",
    response_model=ExamSessionResponse
)
def start_exam(
    request: ExamSessionCreate,
    db: Session = Depends(get_db),
    student: Student = Depends(get_current_student)
):
    return ExamSessionService.start_exam(student, request.exam_id, db)


@router.get(
    "",
    response_model=list[ExamSessionResponse]
)
def get_sessions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return ExamSessionService.get_all(current_user, db)


@router.get(
    "/{session_id}",
    response_model=ExamSessionResponse
)
def get_session(
    session: ExamSession = Depends(require_session_read_access)
):
    return session


@router.put(
    "/submit/{session_id}",
    response_model=ExamSessionResponse
)
def submit_exam(
    session_id: int,
    db: Session = Depends(get_db),
    session: ExamSession = Depends(require_session_owner_student)
):
    return ExamSessionService.submit_exam(session_id, db)


@router.put(
    "/{session_id}/retake-review",
    response_model=ExamSessionResponse
)
def review_retake(
    session_id: int,
    request: RetakeReviewRequest,
    db: Session = Depends(get_db),
    session: ExamSession = Depends(require_session_manage_access)
):
    return ExamSessionService.review_retake(session_id, request.decision, db)


@router.put(
    "/{session_id}",
    response_model=ExamSessionResponse
)
def update_session(
    session_id: int,
    request: ExamSessionUpdate,
    db: Session = Depends(get_db),
    session: ExamSession = Depends(require_session_manage_access)
):
    return ExamSessionService.update(
        session_id,
        request,
        db
    )


@router.delete("/{session_id}")
def delete_session(
    session_id: int,
    db: Session = Depends(get_db),
    session: ExamSession = Depends(require_session_manage_access)
):
    return ExamSessionService.delete(
        session_id,
        db
    )
