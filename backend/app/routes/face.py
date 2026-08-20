from fastapi import APIRouter, Depends, File, Form, UploadFile
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
    # Optional - only used to snapshot context onto a PROLONGED_HEAD_DOWN violation if one fires
    # on this poll; harmless if omitted.
    question_id: int | None = Form(None),
    question_text: str | None = Form(None),
    question_type: str | None = Form(None),
    # True means: the client (MediaPipe Face Detector, running in-browser) already ran its own
    # detection and is confident a face is present, so `file` is a small pre-cropped face region
    # rather than a full frame - see FaceService.verify's client_confident_crop docstring for
    # what this skips server-side. False/absent means `file` is a full raw frame and the existing
    # server-side detection pipeline runs unchanged.
    client_confident_crop: bool = Form(False),
    db: Session = Depends(get_db),
    session: ExamSession = Depends(require_session_owner_student)
):
    image_bytes = await file.read()
    return FaceService.verify(
        session_id,
        image_bytes,
        db,
        question_id=question_id,
        question_text=question_text,
        question_type=question_type,
        client_confident_crop=client_confident_crop
    )
