from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.ownership import require_exam_owner
from app.core.database import get_db
from app.models.exam import Exam
from app.schemas.report import ExamReport
from app.services.report_service import ReportService

router = APIRouter(
    prefix="/exams",
    tags=["Reports"]
)


@router.get(
    "/{exam_id}/report",
    response_model=ExamReport
)
def get_exam_report(
    exam_id: int,
    db: Session = Depends(get_db),
    exam: Exam = Depends(require_exam_owner)
):
    # require_exam_owner already resolved and ownership-checked the exam - previously this used
    # bare require_instructor, so ANY instructor could view ANY exam's report, not just their own.
    return ReportService.get_exam_report(exam.id, db)
