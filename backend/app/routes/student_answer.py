from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.session_access import require_session_owner_student, require_session_read_access
from app.core.database import get_db
from app.models.exam_session import ExamSession
from app.schemas.student_answer import (
    StudentAnswerCreate,
    StudentAnswerResponse,
)
from app.services.student_answer_service import StudentAnswerService

router = APIRouter(
    prefix="/exam-sessions",
    tags=["Student Answers"]
)


@router.post(
    "/{session_id}/answers",
    response_model=StudentAnswerResponse
)
def save_answer(
    session_id: int,
    request: StudentAnswerCreate,
    db: Session = Depends(get_db),
    session: ExamSession = Depends(require_session_owner_student)
):
    return StudentAnswerService.save_answer(
        session_id,
        request,
        db
    )


@router.get(
    "/{session_id}/answers",
    response_model=list[StudentAnswerResponse]
)
def get_answers(
    session_id: int,
    db: Session = Depends(get_db),
    session: ExamSession = Depends(require_session_read_access)
):
    return StudentAnswerService.get_answers(
        session_id,
        db
    )