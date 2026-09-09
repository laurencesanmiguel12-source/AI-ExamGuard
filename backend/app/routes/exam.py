from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, is_super_admin, require_instructor
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
    current_user: User = Depends(require_instructor)
):
    # No instructor is resolved here any more. The section names exactly one, and the service
    # derives it from there - which is also what closed the older hole where an admin could name
    # any instructor in the body and have the exam recorded against them.
    return ExamService.create(current_user, request, db)


@router.put("/{exam_id}", response_model=ExamResponse)
def update_exam(
    exam_id: int,
    request: ExamUpdate,
    db: Session = Depends(get_db),
    exam: Exam = Depends(require_exam_owner),
    current_user: User = Depends(require_instructor),
):
    # current_user as well as the owner check: require_exam_owner proves the caller may change
    # THIS exam, and the service needs to prove separately that they may move it to whatever
    # section the body names.
    return ExamService.update(exam_id, current_user, request, db)


@router.delete("/{exam_id}")
def delete_exam(
    exam_id: int,
    db: Session = Depends(get_db),
    exam: Exam = Depends(require_exam_owner)
):
    return ExamService.delete(exam_id, db)