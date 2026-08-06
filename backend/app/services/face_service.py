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
from app.services.object_detection_service import _POSE_MODEL
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


# COCO-17 pose keypoint index for the nose (matches object_detection_service.py's confirmed
# COCO-pose index convention).
_NOSE_KPT = 0
# Empirically validated 2026-07-31 (backend/training/analyze_pose_fallback_threshold.py) against
# the 290 real frames where YuNet actually fails (using annotation_batch's human-labeled "face"
# class as ground truth, restricted to that YuNet-failed subset - the only place this fallback
# ever runs in production): 268/290 genuinely had a person YuNet just missed, only 22 were truly
# empty. At 0.10, recall = 1.000 (never misses a real head - the safety-critical property, since
# a miss here causes a false FACE_LOST) with precision = 0.944. Raising the threshold only trades
# recall for marginal precision gains, a bad tradeoff given the asymmetric cost. This value was
# originally just borrowed from object_detection_service.py's WRIST_VISIBILITY_THRESHOLD (swept
# for a different keypoint); it turns out to already be on the safe/optimal edge for this use too.
_HEAD_PRESENCE_CONFIDENCE_THRESHOLD = 0.10


def _pose_fallback_signals(image) -> tuple[bool, float]:
    """Fallback for when YuNet finds no face at all. Runs the pose model once and returns two
    *different* signals, because one variable can't safely serve both jobs (tried that, it
    doesn't work - a genuinely bowed head gives a low nose-keypoint confidence for the same
    reason a truly empty scene does: the nose keypoint itself is foreshortened/occluded by the
    downward tilt, so it's not a reliable stand-in for "is anyone here").

    person_present: whether the pose model detected a person box AT ALL, independent of any
    single keypoint's confidence. A student who's just looking down still has a clear torso/
    shoulders square to the camera, so the box detection stays strong even when the nose
    keypoint itself doesn't. This is the signal safe to gate FACE_LOST on - a truly empty scene
    has no person box.

    nose_confidence: highest nose-keypoint confidence across detected people, or 0.0 if none.
    Empirically validated 2026-07-31 (backend/training/analyze_pose_fallback_threshold.py)
    against the 290 real frames where YuNet actually fails (using annotation_batch's
    human-labeled "face" class as ground truth, restricted to that YuNet-failed subset - the
    only place this fallback ever runs in production): 268/290 genuinely had a person YuNet just
    missed, only 22 were truly empty. At 0.10 (_HEAD_PRESENCE_CONFIDENCE_THRESHOLD), recall =
    1.000 (never misses a real head - the safety-critical property, since a miss here causes a
    false negative on the head-down streak) with precision = 0.944. This is deliberately only
    used to decide whether to keep crediting an *existing* head-down streak, never FACE_LOST -
    see the person_present signal above for why."""
    pose_results = _POSE_MODEL.predict(image, verbose=False)[0]

    person_present = pose_results.boxes is not None and len(pose_results.boxes) > 0

    nose_confidence = 0.0
    if pose_results.keypoints is not None:
        for person_kpts in pose_results.keypoints.data:
            _, _, confidence = person_kpts[_NOSE_KPT].tolist()
            nose_confidence = max(nose_confidence, confidence)

    return person_present, nose_confidence


# Empirically checked 2026-07-31 against 2221 human-labeled real frames (phone-present vs.
# phone-absent, backend/training/analyze_head_pose_thresholds.py) - NOT a strong signal. -35 sits
# at the F1 peak (~0.53) across a sweep from -15 to -65, but precision there is only ~0.50: the
# phone-present and phone-absent pitch distributions heavily overlap (median -37.8 vs -30.3,
# both spanning roughly -50 to -15). No threshold value does meaningfully better - this is a
# ceiling of the signal itself (a laptop webcam sits above eye level, so even neutral posture
# reads as persistently negative, and looking down at an exam paper produces a similar pitch to
# looking down at a phone), not a mistuned number. See the gaze-monitoring feasibility memory for
# the full writeup, including why this means duration + human review are doing real work here,
# not just backstopping an already-strong detector.
HEAD_DOWN_PITCH_THRESHOLD_DEGREES = -35.0
# Empirically checked 2026-07-31 against 4 real, densely-timestamped capture sequences
# (backend/training/simulate_head_down_system.py) - 25s comfortably catches the 3 clean subjects'
# real sustained phone-use episodes (28.6s/42.8s/43.0s long) while ignoring sub-2s label-noise
# blips. Kept as-is; the real bug this analysis found was HEAD_DOWN_MISS_TOLERANCE (see below),
# not this value.
HEAD_DOWN_DURATION_THRESHOLD_SECONDS = 25.0
# Consecutive non-down polls forgiven before a streak actually resets. Added 2026-07-31 after the
# same simulation found the ORIGINAL reset-on-any-miss behavior (tolerance implicitly 0) made the
# feature never fire at all across all 4 real sequences, even during obvious 28-43s sustained
# phone-use episodes - a single noisy poll where pitch happened to read just above threshold
# discarded all accumulated progress. Sweeping 0/1/2/3: tolerance=1 fixed every sequence
# (including one where the streak-breaking pattern was severe enough that raising to 2 or 3 made
# no further difference), so 1 is the minimal fix, not a guessed number.
HEAD_DOWN_MISS_TOLERANCE = 1


def _is_head_down(pose: dict | None, head_present_via_fallback: bool = False) -> bool:
    if pose is not None:
        return pose["pitch"] <= HEAD_DOWN_PITCH_THRESHOLD_DEGREES
    # No numeric pose - YuNet found no face at all this poll. If the pose-model fallback still
    # sees a head, the most plausible explanation is that it's angled down enough to lose facial
    # landmarks, not that no one's there - treat this poll as continuing a down streak rather
    # than resetting it. If the fallback *also* sees nothing, this correctly falls through to
    # False (a real FACE_LOST, handled by the caller).
    return head_present_via_fallback


def _track_head_down(
    session: ExamSession,
    pose: dict | None,
    head_present_via_fallback: bool = False
) -> tuple[float, bool]:
    """Updates the session's head-down streak state from the latest poll's pose estimate.
    Persisted on the session (not kept in-memory) since a 5s poll can't tell duration from a
    single snapshot and an in-memory timer would silently reset on a backend restart mid-exam.

    Returns (current continuous streak duration in seconds, whether *this* poll is the one that
    should trigger a violation). The flag is True exactly once per streak - the poll where
    duration first crosses HEAD_DOWN_DURATION_THRESHOLD_SECONDS - not on every subsequent poll
    while the student stays down, which is what head_down_violation_logged exists to prevent.

    Up to HEAD_DOWN_MISS_TOLERANCE consecutive non-down polls are forgiven without resetting the
    streak - see that constant's comment for why an untolerant reset made this never fire in
    practice. A forgiven miss doesn't advance head_down_consecutive_count or trigger a violation
    on its own; it just doesn't discard progress already made."""
    if _is_head_down(pose, head_present_via_fallback):
        session.head_down_miss_streak = 0
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

    session.head_down_miss_streak += 1
    if session.head_down_miss_streak > HEAD_DOWN_MISS_TOLERANCE:
        session.head_down_since = None
        session.head_down_consecutive_count = 0
        session.head_down_violation_logged = False
        session.head_down_miss_streak = 0
        return 0.0, False

    # Within tolerance - streak survives, but this poll itself doesn't advance or fire anything.
    if session.head_down_since is None:
        return 0.0, False
    duration = (datetime.now(timezone.utc) - session.head_down_since).total_seconds()
    return duration, False


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

        # YuNet found no face at all - before concluding no one's there, check the pose-model
        # fallback. A live smoke-test (2026-07-31) found a real head-down tilt can make YuNet
        # lose facial landmarks entirely, well before pitch would cross the down threshold - so
        # treating "no face landmarks" as automatically "no head" made this feature nearly
        # untriggerable by the exact behavior it exists to catch. See
        # _pose_fallback_signals's docstring for why this needs two separate signals, not one.
        person_present, fallback_confidence = (
            _pose_fallback_signals(image) if detection is None and image is not None
            else (False, 0.0)
        )
        head_present_via_fallback = fallback_confidence >= _HEAD_PRESENCE_CONFIDENCE_THRESHOLD

        head_down_duration, should_log_head_down = _track_head_down(
            session, pose, head_present_via_fallback
        )
        db.commit()

        if should_log_head_down:
            # Evidence here is deliberately *not* a webcam frame - it's a weaker, geometric proxy
            # signal (head pose, not eye gaze), not a direct visual identification, so it isn't in
            # EVIDENCE_EVENT_TYPES. The question-context snapshot below is the real evidence: lets
            # a reviewer judge plausibility ("one multiple-choice line, no reason to look away
            # that long" vs "a 500-word essay question") without a screenshot.
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
            # Gated on person_present (any pose-model person box), not fallback_confidence (a
            # single keypoint's confidence) - a real head-down poll can have a low nose-keypoint
            # confidence for the same reason an empty scene does, so that signal can't tell the
            # two apart. The box detection can: a bowed head still has a clear torso/shoulders in
            # frame.
            if not person_present:
                ViolationService.log_violation(
                    session_id,
                    ViolationCreate(event_type="FACE_LOST"),
                    db,
                    evidence_bytes=image_bytes
                )
            return {
                "face_detected": False,
                "identity_match": False,
                "confidence": None,
                "person_present": person_present
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
