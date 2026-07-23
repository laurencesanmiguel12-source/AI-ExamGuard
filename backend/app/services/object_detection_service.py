import os

import numpy as np
from sqlalchemy.orm import Session
from ultralytics import YOLO

from app.schemas.violation import ViolationCreate
from app.services.violation_service import ViolationService

MODEL_PATH = os.path.join(
    os.path.dirname(__file__), "..", "resources", "yolov8s.pt"
)

PERSON_CLASS = 0
CELL_PHONE_CLASS = 67
# Lower than the YOLO default (0.25) would suggest is "risky" for general detection, but tuned up
# from an initial 0.5: real-world testing showed 0.5 missed phones held at an angle or shown
# back-first, since COCO's "cell phone" class skews toward front-facing/screen-visible phones.
CONFIDENCE_THRESHOLD = 0.35

_MODEL = YOLO(MODEL_PATH)


def _decode(image_bytes: bytes):
    import cv2

    array = np.frombuffer(image_bytes, dtype=np.uint8)
    return cv2.imdecode(array, cv2.IMREAD_COLOR)


class ObjectDetectionService:

    @staticmethod
    def check(
        session_id: int,
        image_bytes: bytes,
        db: Session
    ):

        image = _decode(image_bytes)

        if image is None:
            return {"phone_detected": False, "person_count": 0}

        results = _MODEL.predict(image, verbose=False, conf=CONFIDENCE_THRESHOLD)[0]

        classes = results.boxes.cls.tolist() if results.boxes is not None else []

        phone_detected = CELL_PHONE_CLASS in classes
        person_count = classes.count(PERSON_CLASS)

        if phone_detected:
            ViolationService.log_violation(
                session_id,
                ViolationCreate(event_type="PHONE_DETECTED"),
                db
            )

        if person_count > 1:
            ViolationService.log_violation(
                session_id,
                ViolationCreate(event_type="MULTIPLE_PEOPLE"),
                db
            )

        return {
            "phone_detected": phone_detected,
            "person_count": person_count
        }
