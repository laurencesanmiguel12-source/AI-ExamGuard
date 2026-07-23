import os

import cv2
import numpy as np
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.exam_session import ExamSession
from app.models.student import Student
from app.schemas.violation import ViolationCreate
from app.services.violation_service import ViolationService

FACE_SIZE = (200, 200)
MIN_ENROLLMENT_SAMPLES = 3
CONFIDENCE_THRESHOLD = 80.0

STORAGE_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "storage",
    "face_models"
)

_CASCADE_PATH = os.path.join(
    os.path.dirname(__file__), "..", "resources", "haarcascade_frontalface_default.xml"
)
_CASCADE = cv2.CascadeClassifier(_CASCADE_PATH)


def _detect_and_crop(image_bytes: bytes):
    array = np.frombuffer(image_bytes, dtype=np.uint8)
    image = cv2.imdecode(array, cv2.IMREAD_COLOR)

    if image is None:
        return None

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    faces = _CASCADE.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5)

    if len(faces) == 0:
        return None

    x, y, w, h = max(faces, key=lambda f: f[2] * f[3])
    crop = gray[y:y + h, x:x + w]

    return cv2.resize(crop, FACE_SIZE)


class FaceService:

    @staticmethod
    def enroll(
        student_id: int,
        image_bytes_list: list[bytes],
        db: Session
    ):

        student = (
            db.query(Student)
            .filter(Student.id == student_id)
            .first()
        )

        if student is None:
            raise HTTPException(
                status_code=404,
                detail="Student not found."
            )

        samples = []
        for image_bytes in image_bytes_list:
            crop = _detect_and_crop(image_bytes)
            if crop is not None:
                samples.append(crop)

        if len(samples) < MIN_ENROLLMENT_SAMPLES:
            raise HTTPException(
                status_code=400,
                detail="Couldn't detect a clear face in enough images — try again with better lighting."
            )

        labels = np.array([student_id] * len(samples))

        recognizer = cv2.face.LBPHFaceRecognizer_create()
        recognizer.train(samples, labels)

        os.makedirs(STORAGE_DIR, exist_ok=True)
        model_path = os.path.join(STORAGE_DIR, f"{student_id}.yml")
        recognizer.write(model_path)

        student.face_model_path = model_path
        db.commit()

        return {
            "enrolled": True,
            "samples_used": len(samples)
        }

    @staticmethod
    def verify(
        session_id: int,
        image_bytes: bytes,
        db: Session
    ):

        session = (
            db.query(ExamSession)
            .filter(ExamSession.id == session_id)
            .first()
        )

        if session is None:
            raise HTTPException(
                status_code=404,
                detail="Exam session not found."
            )

        student = (
            db.query(Student)
            .filter(Student.id == session.student_id)
            .first()
        )

        if student is None or student.face_model_path is None:
            return {
                "face_detected": None,
                "identity_match": None,
                "confidence": None
            }

        crop = _detect_and_crop(image_bytes)

        if crop is None:
            ViolationService.log_violation(
                session_id,
                ViolationCreate(event_type="FACE_LOST"),
                db
            )
            return {
                "face_detected": False,
                "identity_match": False,
                "confidence": None
            }

        recognizer = cv2.face.LBPHFaceRecognizer_create()
        recognizer.read(student.face_model_path)

        label, confidence = recognizer.predict(crop)
        match = label == student.id and confidence < CONFIDENCE_THRESHOLD

        if not match:
            ViolationService.log_violation(
                session_id,
                ViolationCreate(event_type="IDENTITY_MISMATCH"),
                db
            )

        return {
            "face_detected": True,
            "identity_match": match,
            "confidence": float(confidence)
        }
