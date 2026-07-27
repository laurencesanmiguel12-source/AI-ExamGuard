from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session

from app.auth.session_access import require_own_student, require_session_owner_student
from app.core.database import get_db
from app.models.exam_session import ExamSession
from app.models.student import Student
from app.schemas.face import FaceCheckResponse, FaceEnrollResponse
from app.services.face_service import FaceService

router = APIRouter(tags=["Face Enrollment"])


@router.post(
    "/students/{student_id}/face-enrollment",
    response_model=FaceEnrollResponse
)
async def enroll_face(
    student_id: int,
    files: list[UploadFile] = File(...),
    db: Session = Depends(get_db),
    student: Student = Depends(require_own_student)
):
    image_bytes_list = [await f.read() for f in files]
    return FaceService.enroll(student_id, image_bytes_list, db)


@router.post(
    "/exam-sessions/{session_id}/face-check",
    response_model=FaceCheckResponse
)
async def check_face(
    session_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    session: ExamSession = Depends(require_session_owner_student)
):
    image_bytes = await file.read()
    return FaceService.verify(session_id, image_bytes, db)
