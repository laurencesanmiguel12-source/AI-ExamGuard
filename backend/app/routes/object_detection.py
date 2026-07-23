from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session

from app.core.database import get_db
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
    db: Session = Depends(get_db)
):
    image_bytes = await file.read()
    return ObjectDetectionService.check(session_id, image_bytes, db)
