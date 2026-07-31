import math
import os
import time
from datetime import datetime, timezone

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

_YUNET_PATH = os.path.join(
    os.path.dirname(__file__), "..", "resources", "face_detection_yunet_2023mar.onnx"
)
# YuNet replaces the old Haar cascade - unlike Haar's frontal-only detection (reliable only within
# roughly +/-15-20 degrees of straight-on), YuNet is a small pretrained ONNX model built and
# benchmarked specifically for pose/rotation/lighting robustness, fixing detection dropping out on
# quick head turns. Score/NMS thresholds are OpenCV's own sample defaults - a starting point, not
# yet tuned against real hardware.
_DETECTOR = cv2.FaceDetectorYN_create(
    _YUNET_PATH, "", (320, 320), score_threshold=0.9, nms_threshold=0.3, top_k=5000
)

# Fixed size matching a typical ExamRoom capture frame - reused across benchmark calls so the
# Admin System tab measures real detector latency on this hardware, not a fabricated number.
_BENCHMARK_IMAGE = np.zeros((480, 640, 3), dtype=np.uint8)


def _detect_largest_face(image):
    # YuNet expects a color image and needs the actual per-frame size set before each detect()
    # call, since captured frame dimensions aren't guaranteed constant across requests.
    _DETECTOR.setInputSize((image.shape[1], image.shape[0]))
    _, faces = _DETECTOR.detect(image)

    if faces is None or len(faces) == 0:
        return None

    # Row layout: x, y, w, h, then 5 landmarks (right eye, left eye, nose tip, right mouth
    # corner, left mouth corner) as x,y pairs, then a confidence score - 15 values total.
    return max(faces, key=lambda f: f[2] * f[3])


def _crop_from_detection(image, detection):
    x, y, w, h = detection[:4].astype(int)
    x, y = max(x, 0), max(y, 0)

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    crop = gray[y:y + h, x:x + w]

    if crop.size == 0:
        return None

    return cv2.resize(crop, FACE_SIZE)


def _detect_and_crop(image_bytes: bytes):
    array = np.frombuffer(image_bytes, dtype=np.uint8)
    image = cv2.imdecode(array, cv2.IMREAD_COLOR)

    if image is None:
        return None

    detection = _detect_largest_face(image)
    if detection is None:
        return None

    return _crop_from_detection(image, detection)


# Generic adult-face 3D reference points (approximate proportions on an arbitrary mm-like
# scale - solvePnP's recovered rotation is scale-invariant, so what matters is getting the
# relative proportions roughly right, not the exact unit). Order matches YuNet's landmark
# output: right eye, left eye, nose tip, right mouth corner, left mouth corner. +X = subject's
# right, +Z = toward the camera (nose tip is the forward-most point). +Y = DOWN, matching
# OpenCV's camera-frame convention (image row index increases downward) - eyes get a
# *negative* Y (toward the top of frame) and the mouth a positive one, not the anatomically
# "natural" Y-up you'd reach for first. Getting this backwards doesn't error, it just leaves
# solvePnP to find the ~180-degree corrective flip, which is what happened on the first pass.
_FACE_MODEL_3D = np.array([
    [-30.0, -35.0, -30.0],  # right eye center
    [30.0, -35.0, -30.0],  # left eye center
    [0.0,   0.0,   0.0],  # nose tip
    [-25.0,  35.0, -20.0],  # right mouth corner
    [25.0,  35.0, -20.0],  # left mouth corner
], dtype=np.float64)


def _camera_matrix(width: int, height: int) -> np.ndarray:
    # No real calibration data for arbitrary student webcams, so approximate focal length as
    # the image width in pixels - the standard stand-in used when true calibration isn't
    # available (classic OpenCV head-pose approximation).
    focal_length = width
    center_x, center_y = width / 2, height / 2
    return np.array([
        [focal_length, 0, center_x],
        [0, focal_length, center_y],
        [0, 0, 1],
    ], dtype=np.float64)


def _rotation_matrix_to_euler(rotation_matrix: np.ndarray) -> tuple[float, float, float]:
    """(pitch, yaw, roll) in degrees. Positive pitch = chin tilted down (head rotated
    forward/down); positive yaw = turned toward the subject's left; positive roll =
    tilted toward the subject's left shoulder."""
    sy = math.sqrt(rotation_matrix[0, 0] ** 2 + rotation_matrix[1, 0] ** 2)
    singular = sy < 1e-6

    if not singular:
        pitch = math.atan2(rotation_matrix[2, 1], rotation_matrix[2, 2])
        yaw = math.atan2(-rotation_matrix[2, 0], sy)
        roll = math.atan2(rotation_matrix[1, 0], rotation_matrix[0, 0])
    else:
        pitch = math.atan2(-rotation_matrix[1, 2], rotation_matrix[1, 1])
        yaw = math.atan2(-rotation_matrix[2, 0], sy)
        roll = 0.0

    return math.degrees(pitch), math.degrees(yaw), math.degrees(roll)


def _estimate_head_pose(image, detection) -> dict | None:
    """Head *pose* (pitch/yaw/roll), not eye gaze, from YuNet's 5 sparse landmarks via
    cv2.solvePnP against a generic 3D face model. Deliberately the weaker, cheaper signal:
    a student can look down with just their eyes while keeping their head level, so this
    is a proxy for "head aimed down," not a claim about where the eyes are pointed."""
    height, width = image.shape[:2]
    landmarks_2d = detection[4:14].reshape(5, 2).astype(np.float64)

    camera_matrix = _camera_matrix(width, height)
    dist_coeffs = np.zeros((4, 1))

    # SOLVEPNP_ITERATIVE's initial-guess step needs >=6 points in this OpenCV build; EPnP
    # supports our 5 non-coplanar landmarks directly.
    success, rotation_vector, _ = cv2.solvePnP(
        _FACE_MODEL_3D, landmarks_2d, camera_matrix, dist_coeffs,
        flags=cv2.SOLVEPNP_EPNP
    )
    if not success:
        return None

    rotation_matrix, _ = cv2.Rodrigues(rotation_vector)
    pitch, yaw, roll = _rotation_matrix_to_euler(rotation_matrix)
    return {"pitch": pitch, "yaw": yaw, "roll": roll}


# Placeholder, NOT yet empirically validated - see the plan's later "empirical threshold
# tuning" step. The pitch threshold in particular is fragile: a laptop webcam is typically
# mounted above eye level looking down at the user, so even a neutral, forward-facing pose
# reads as a persistent negative pitch offset (confirmed against real capture data during the
# head-pose smoke test - see test_head_pose.py) rather than ~0deg. A single fixed global
# degrees threshold may not survive contact with varied camera placements and will likely need
# to become a per-session calibrated baseline once real head-down data is collected - same
# lesson as the phone-detection confidence-threshold work.
HEAD_DOWN_PITCH_THRESHOLD_DEGREES = -35.0
# Candidate from the plan (20-30s, "longer than a normal typing glance"), also unvalidated.
HEAD_DOWN_DURATION_THRESHOLD_SECONDS = 25.0


def _is_head_down(pose: dict | None) -> bool:
    return pose is not None and pose["pitch"] <= HEAD_DOWN_PITCH_THRESHOLD_DEGREES


def _track_head_down(session: ExamSession, pose: dict | None) -> tuple[float, bool]:
    """Updates the session's head-down streak state from the latest poll's pose estimate.
    Persisted on the session (not kept in-memory) since a 5s poll can't tell duration from a
    single snapshot and an in-memory timer would silently reset on a backend restart mid-exam.

    Returns (current continuous streak duration in seconds, whether *this* poll is the one that
    should trigger a violation). The flag is True exactly once per streak - the poll where
    duration first crosses HEAD_DOWN_DURATION_THRESHOLD_SECONDS - not on every subsequent poll
    while the student stays down, which is what head_down_violation_logged exists to prevent."""
    if not _is_head_down(pose):
        session.head_down_since = None
        session.head_down_consecutive_count = 0
        session.head_down_violation_logged = False
        return 0.0, False

    now = datetime.now(timezone.utc)
    if session.head_down_since is None:
        session.head_down_since = now

    session.head_down_consecutive_count += 1
    duration = (now - session.head_down_since).total_seconds()

    should_log = (
        duration >= HEAD_DOWN_DURATION_THRESHOLD_SECONDS
        and not session.head_down_violation_logged
    )
    if should_log:
        session.head_down_violation_logged = True

    return duration, should_log


class FaceService:

    @staticmethod
    def benchmark_latency_ms() -> float:
        start = time.perf_counter()
        _DETECTOR.setInputSize((640, 480))
        _DETECTOR.detect(_BENCHMARK_IMAGE)
        return round((time.perf_counter() - start) * 1000, 1)

    @staticmethod
    def estimate_head_pose(image_bytes: bytes) -> dict | None:
        """Returns {"pitch", "yaw", "roll"} in degrees for the largest detected face, or
        None if no face is found. Standalone for now (duration-tracking, thresholds, and
        violation wiring come later) - not yet called from verify()."""
        array = np.frombuffer(image_bytes, dtype=np.uint8)
        image = cv2.imdecode(array, cv2.IMREAD_COLOR)

        if image is None:
            return None

        detection = _detect_largest_face(image)
        if detection is None:
            return None

        return _estimate_head_pose(image, detection)

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
        db: Session,
        question_id: int | None = None,
        question_text: str | None = None,
        question_type: str | None = None
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

        if student is None or student.face_model_path is None or student.skip_face_check:
            return {
                "face_detected": None,
                "identity_match": None,
                "confidence": None
            }

        array = np.frombuffer(image_bytes, dtype=np.uint8)
        image = cv2.imdecode(array, cv2.IMREAD_COLOR)

        # Single detect() call feeds both the identity crop and the head-pose estimate below -
        # no extra model cost for tracking head-down duration on top of the existing check.
        detection = _detect_largest_face(image) if image is not None else None
        pose = _estimate_head_pose(image, detection) if detection is not None else None
        head_down_duration, should_log_head_down = _track_head_down(session, pose)
        db.commit()

        if should_log_head_down:
            # Evidence here is deliberately *not* a webcam frame - it's a weaker, geometric proxy
            # signal (head pose, not eye gaze), not a direct visual identification, so it isn't in
            # EVIDENCE_EVENT_TYPES. The question-context snapshot below is the real evidence: lets
            # a reviewer judge plausibility ("one multiple-choice line, no reason to look away
            # that long" vs "a 500-word essay question") without a screenshot. question_id/
            # text/type are None until the frontend actually sends the current question with each
            # poll - that wiring doesn't exist yet, so this stays a no-op for now.
            ViolationService.log_violation(
                session_id,
                ViolationCreate(
                    event_type="PROLONGED_HEAD_DOWN",
                    detail=f"{head_down_duration:.0f}s continuous"
                ),
                db,
                question_id=question_id,
                question_text=question_text,
                question_type=question_type
            )

        crop = _crop_from_detection(image, detection) if detection is not None else None

        if crop is None:
            ViolationService.log_violation(
                session_id,
                ViolationCreate(event_type="FACE_LOST"),
                db,
                evidence_bytes=image_bytes
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
                db,
                evidence_bytes=image_bytes
            )

        return {
            "face_detected": True,
            "identity_match": match,
            "confidence": float(confidence)
        }
