from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.auth.instructor_context import get_current_instructor
from app.auth.ownership import require_exam_owner
from app.core.database import get_db
from app.models.exam import Exam
from app.models.instructor import Instructor
from app.models.user import User
from app.schemas.exam import ExamCreate, ExamUpdate, ExamResponse
from app.services.exam_service import ExamService

router = APIRouter(
    prefix="/exams",
    tags=["Exams"]
)


@router.get("/", response_model=list[ExamResponse])
def get_exams(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return ExamService.get_all(current_user, db)


@router.get("/{exam_id}", response_model=ExamResponse)
def get_exam(
    exam_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return ExamService.get_by_id_for_user(exam_id, current_user, db)


@router.post("/", response_model=ExamResponse)
def create_exam(
    request: ExamCreate,
    db: Session = Depends(get_db),
    instructor: Instructor = Depends(get_current_instructor)
):
    return ExamService.create(instructor, request, db)


@router.put("/{exam_id}", response_model=ExamResponse)
def update_exam(
    exam_id: int,
    request: ExamUpdate,
    db: Session = Depends(get_db),
    exam: Exam = Depends(require_exam_owner)
):
    return ExamService.update(exam_id, request, db)


@router.delete("/{exam_id}")
def delete_exam(
    exam_id: int,
    db: Session = Depends(get_db),
    exam: Exam = Depends(require_exam_owner)
):
    return ExamService.delete(exam_id, db)