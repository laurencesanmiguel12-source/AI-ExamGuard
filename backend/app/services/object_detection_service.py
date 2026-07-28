import os
import time

import numpy as np
from sqlalchemy.orm import Session
from ultralytics import YOLO

from app.models.exam_session import ExamSession
from app.models.student import Student
from app.schemas.violation import ViolationCreate
from app.services.violation_service import ViolationService

MODEL_PATH = os.path.join(
    os.path.dirname(__file__), "..", "resources", "yolov8s.pt"
)
PHONE_MODEL_PATH = os.path.join(
    os.path.dirname(__file__), "..", "resources", "phone_specialist.pt"
)
POSE_MODEL_PATH = os.path.join(
    os.path.dirname(__file__), "..", "resources", "yolov8n-pose.pt"
)

PERSON_CLASS = 0
CELL_PHONE_CLASS = 67
# Lower than the YOLO default (0.25) would suggest is "risky" for general detection, but tuned up
# from an initial 0.5: real-world testing showed 0.5 missed phones held at an angle or shown
# back-first, since COCO's "cell phone" class skews toward front-facing/screen-visible phones.
CONFIDENCE_THRESHOLD = 0.35
# Not yet tuned against real hardware - same starting-point-then-adjust approach as
# CONFIDENCE_THRESHOLD above, applied to the fine-tuned specialist below.
PHONE_SPECIALIST_CONFIDENCE_THRESHOLD = 0.35
PHONE_SPECIALIST_CLASS = 0  # single-class model (see backend/training/prepare_dataset.py)

# COCO-17 keypoint indices (confirmed against ultralytics' own coco-pose.yaml, not assumed).
LEFT_WRIST_KPT = 9
RIGHT_WRIST_KPT = 10
WRIST_VISIBILITY_THRESHOLD = 0.5
HAND_CROP_SIZE = 120  # pixels, fixed starting point - see plan notes on scaling to shoulder width
# Deliberately lower than PHONE_SPECIALIST_CONFIDENCE_THRESHOLD: narrowing the search to "right
# where a hand is" is what makes a lower threshold safe here, catching phones (e.g. held sideways)
# that don't score high enough on a whole-frame pass. Not yet tuned against real hardware.
HAND_REGION_PHONE_THRESHOLD = 0.20

# The base COCO model still handles person-counting (its "cell phone" class stays unused here -
# base_yolov8s.pt's own phone signal was the accuracy problem in the first place). The specialist
# below was fine-tuned specifically on phone images (backend/training/finetune_phone.py) and is a
# single-class model with no "person" class at all, so the two models are deliberately kept
# separate rather than one replacing the other - see backend/training/finetune_phone.py's docstring
# for why a combined single model isn't used. The pose model is used only for wrist location, to
# focus a second, more sensitive phone-specialist pass on hand regions - see the project plan for
# why (sideways-held phones are hard to recognize by shape alone from a whole-frame pass).
_MODEL = YOLO(MODEL_PATH)
_PHONE_MODEL = YOLO(PHONE_MODEL_PATH)
_POSE_MODEL = YOLO(POSE_MODEL_PATH)

# Matches a typical ExamRoom capture frame - reused across benchmark calls so the Admin System
# tab measures real inference latency on this hardware, not a fabricated number. Only the base +
# phone-specialist models are timed, matching the common-case path in `check()` below - the pose
# model only runs when the specialist misses, so isn't part of the steady-state cost.
_BENCHMARK_IMAGE = np.zeros((480, 640, 3), dtype=np.uint8)


def _decode(image_bytes: bytes):
    import cv2

    array = np.frombuffer(image_bytes, dtype=np.uint8)
    return cv2.imdecode(array, cv2.IMREAD_COLOR)


def _wrist_points(pose_results, image_shape):
    height, width = image_shape[:2]
    points = []

    if pose_results.keypoints is None:
        return points

    for person_kpts in pose_results.keypoints.data:
        for idx in (LEFT_WRIST_KPT, RIGHT_WRIST_KPT):
            x, y, conf = person_kpts[idx].tolist()
            if conf >= WRIST_VISIBILITY_THRESHOLD:
                points.append((min(max(int(x), 0), width), min(max(int(y), 0), height)))

    return points


def _hand_crop(image, x, y):
    height, width = image.shape[:2]
    half = HAND_CROP_SIZE // 2

    x1, y1 = max(x - half, 0), max(y - half, 0)
    x2, y2 = min(x + half, width), min(y + half, height)

    if x2 <= x1 or y2 <= y1:
        return None

    return image[y1:y2, x1:x2]


def _phone_near_hands(image, pose_results):
    for x, y in _wrist_points(pose_results, image.shape):
        crop = _hand_crop(image, x, y)
        if crop is None or crop.size == 0:
            continue

        crop_results = _PHONE_MODEL.predict(crop, verbose=False, conf=HAND_REGION_PHONE_THRESHOLD)[0]
        crop_classes = crop_results.boxes.cls.tolist() if crop_results.boxes is not None else []
        if PHONE_SPECIALIST_CLASS in crop_classes:
            return True

    return False


class ObjectDetectionService:

    @staticmethod
    def benchmark_latency_ms() -> float:
        start = time.perf_counter()
        _MODEL.predict(_BENCHMARK_IMAGE, verbose=False, conf=CONFIDENCE_THRESHOLD)
        _PHONE_MODEL.predict(_BENCHMARK_IMAGE, verbose=False, conf=PHONE_SPECIALIST_CONFIDENCE_THRESHOLD)
        return round((time.perf_counter() - start) * 1000, 1)

    @staticmethod
    def check(
        session_id: int,
        image_bytes: bytes,
        db: Session
    ):

        session = db.query(ExamSession).filter(ExamSession.id == session_id).first()
        student = (
            db.query(Student).filter(Student.id == session.student_id).first()
            if session is not None else None
        )

        # Skip inference entirely for an accommodated student, not just the violation-logging
        # step - avoids burning CPU on a check whose result will never be used.
        if student is not None and student.skip_object_check:
            return {"phone_detected": False, "person_count": 0}

        image = _decode(image_bytes)

        if image is None:
            return {"phone_detected": False, "person_count": 0}

        results = _MODEL.predict(image, verbose=False, conf=CONFIDENCE_THRESHOLD)[0]
        classes = results.boxes.cls.tolist() if results.boxes is not None else []
        person_count = classes.count(PERSON_CLASS)

        phone_results = _PHONE_MODEL.predict(
            image, verbose=False, conf=PHONE_SPECIALIST_CONFIDENCE_THRESHOLD
        )[0]
        phone_classes = phone_results.boxes.cls.tolist() if phone_results.boxes is not None else []
        phone_detected = PHONE_SPECIALIST_CLASS in phone_classes

        if not phone_detected:
            pose_results = _POSE_MODEL.predict(image, verbose=False)[0]
            phone_detected = _phone_near_hands(image, pose_results)

        if phone_detected:
            ViolationService.log_violation(
                session_id,
                ViolationCreate(event_type="PHONE_DETECTED"),
                db,
                evidence_bytes=image_bytes
            )

        if person_count > 1:
            ViolationService.log_violation(
                session_id,
                ViolationCreate(event_type="MULTIPLE_PEOPLE"),
                db,
                evidence_bytes=image_bytes
            )

        return {
            "phone_detected": phone_detected,
            "person_count": person_count
        }
