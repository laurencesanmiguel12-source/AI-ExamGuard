from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.ownership import require_exam_owner
from app.core.database import get_db
from app.models.exam import Exam
from app.schemas.exam_roster import ExamRosterCreate, ExamRosterWithStudentResponse
from app.schemas.student import StudentResponse
from app.services.exam_roster_service import ExamRosterService

router = APIRouter(prefix="/exams", tags=["Exam Roster"])


@router.get(
    "/{exam_id}/roster",
    response_model=list[ExamRosterWithStudentResponse]
)
def list_exam_roster(
    db: Session = Depends(get_db),
    exam: Exam = Depends(require_exam_owner)
):
    return ExamRosterService.get_all_for_exam(exam, db)


@router.get(
    "/{exam_id}/roster/available",
    response_model=list[StudentResponse]
)
def list_available_roster_students(
    db: Session = Depends(get_db),
    exam: Exam = Depends(require_exam_owner)
):
    return ExamRosterService.get_available_students(exam, db)


@router.post(
    "/{exam_id}/roster",
    response_model=ExamRosterWithStudentResponse
)
def add_exam_roster_student(
    request: ExamRosterCreate,
    db: Session = Depends(get_db),
    exam: Exam = Depends(require_exam_owner)
):
    return ExamRosterService.add_student(exam, request, db)


@router.delete("/{exam_id}/roster/{student_id}")
def remove_exam_roster_student(
    student_id: int,
    db: Session = Depends(get_db),
    exam: Exam = Depends(require_exam_owner)
):
    return ExamRosterService.remove_student(exam, student_id, db)
