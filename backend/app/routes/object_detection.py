from fastapi import APIRouter, Depends, File, UploadFile
from starlette.concurrency import run_in_threadpool
from sqlalchemy.orm import Session

from app.auth.session_access import require_session_owner_student
from app.core.database import get_db
from app.models.exam_session import ExamSession
from app.schemas.object_detection import ObjectCheckResponse
from app.services.object_detection_service import ObjectDetectionService

router = APIRouter(tags=["Object Detection"])


@router.post(
    "/exam-sessions/{session_id}/object-check",
    response_model=ObjectCheckResponse
)
async def check_objects(
    session_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    session: ExamSession = Depends(require_session_owner_student)
):
    image_bytes = await file.read()
    # Off the event loop: ObjectDetectionService.check is seconds of blocking CPU-bound YOLO
    # inference, and awaiting it inline on a single-worker uvicorn stalls EVERY other request in
    # the app behind it - measured 2026-09-07, this one change took client-crop face-check p50
    # from 970ms to 16ms at 10 concurrent students. Safe only because the YOLO models it reaches
    # are now per-thread (see object_detection_service.py's _thread_models).
    return await run_in_threadpool(ObjectDetectionService.check, session_id, image_bytes, db)
