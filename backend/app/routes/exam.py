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
    if current_user.role.name.lower() == "instructor":
        instructor = db.query(Instructor).filter(Instructor.user_id == current_user.id).first()
        if instructor is None:
            raise HTTPException(status_code=404, detail="No instructor profile linked to this account.")
    else:
        instructor = db.query(Instructor).filter(Instructor.id == request.instructor_id).first()
        if instructor is None:
            raise HTTPException(status_code=404, detail="Instructor not found.")
        if not is_super_admin(current_user) and instructor.user.school_id != current_user.school_id:
            raise HTTPException(status_code=403, detail="You do not have permission to assign this instructor.")
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