import os
import time
from collections import deque

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
# REVERTED 2026-07-30. Was briefly raised to 0.70 the same day based on a frozen-holdout
# precision/recall sweep (see ai_examguard_frozen_holdout_eval memory), but a live browser
# smoke-test immediately after the swap caught a severe real-world regression: 25 live frames of a
# genuine, continuously-held phone were captured and run through the full deployed pipeline
# (whole-frame + pose fallback) - at 0.70 only 1/24 phone-visible frames were flagged (4% recall);
# at the sweep's own "F1-optimal" 0.60 only 3/24 (12.5%); only the original 0.35 caught a usable
# fraction (20/24, 83%). The fallback fired zero times in this test. Reverted to 0.35 as the only
# value that survived live testing - see ai_examguard_threshold_sweep_investigation memory for the
# ongoing investigation into why the offline sweep was this misleading. Do not re-raise this
# without a live smoke-test confirming recall on real, continuously-captured phone frames, not just
# frozen-holdout aggregate numbers.
PHONE_SPECIALIST_CONFIDENCE_THRESHOLD = 0.35
PHONE_SPECIALIST_CLASS = 0  # single-class model (see backend/training/prepare_dataset.py)

# COCO-17 keypoint indices (confirmed against ultralytics' own coco-pose.yaml, not assumed).
LEFT_WRIST_KPT = 9
RIGHT_WRIST_KPT = 10
# Lowered from 0.5 (2026-07-29): a real missed-phone case on live hardware traced back to the
# wrist keypoint itself scoring low (0.10-0.15) because the phone held close to the chest partly
# occludes the wrist joint, blocking the hand-crop fallback from ever running. A sample of OEP val
# frames showed a clean gap between genuinely-visible wrists (0.2-0.7) and genuinely-absent wrists
# (0.02-0.06) - 0.10 sits above that noise floor with real margin while still catching this case.
WRIST_VISIBILITY_THRESHOLD = 0.10
# Raised from 120 to 320 (2026-07-30): the live smoke-test that caught the confidence-threshold
# regression (see ai_examguard_threshold_sweep_investigation memory) also found the fallback fired
# ZERO times across 25 live frames of a genuinely, continuously held phone - a 120px crop centered
# on the wrist joint only reaches the knuckles when a phone is held extended past the fingers (a
# very natural grip), cutting the phone body out of the crop entirely. Confirmed empirically, not
# guessed: swept crop sizes against the same 24 live phone-visible frames (0% hit at 120/160px,
# 25% at 200, 33% at 240, 38% at 280, 71% at 320) and checked false-positive cost against 40
# genuinely phone-negative frozen-holdout frames (2/40 at 320px, barely rising to 3/40 at 360-400px
# while recall gave back a couple points) - 320 is the empirical sweet spot, not a guess scaled up
# arbitrarily. Scaling by shoulder width instead of a fixed pixel size is still a real improvement
# to make later (a person's apparent hand size changes with camera distance), just not done yet.
HAND_CROP_SIZE = 320
# Deliberately lower than PHONE_SPECIALIST_CONFIDENCE_THRESHOLD: narrowing the search to "right
# where a hand is" is what makes a lower threshold safe here, catching phones (e.g. held sideways)
# that don't score high enough on a whole-frame pass. Not yet tuned against real hardware.
HAND_REGION_PHONE_THRESHOLD = 0.20

# Temporal aggregation for the whole-frame phone-specialist pass, added to recover recall on
# frames that fall just under PHONE_SPECIALIST_CONFIDENCE_THRESHOLD without lowering that
# threshold globally - lowering the single-frame bar was never tried directly, but raising it
# (see the note above) already proved single-frame threshold changes are risky without a live
# smoke-test, so this corroborates across polls instead of trusting one frame. A frame scoring
# between the candidate and full threshold only becomes a violation once seen at least
# CANDIDATE_CORROBORATION_COUNT times in the last CANDIDATE_WINDOW_SIZE polls (~15s apart in
# ExamRoom), so a single low-confidence blip can't trigger a false positive on its own.
# NOT YET LIVE-VALIDATED - these two constants are a reasoned starting point, not swept against
# real hardware like HAND_CROP_SIZE/WRIST_VISIBILITY_THRESHOLD were. Confirm with a live
# smoke-test (same method as the threshold-sweep investigation) before trusting this in production.
PHONE_CANDIDATE_THRESHOLD = 0.20
CANDIDATE_WINDOW_SIZE = 3
CANDIDATE_CORROBORATION_COUNT = 2

# ponytail: in-memory per-session state, lost on restart and not safe across multiple worker
# processes - acceptable here since it only spans one exam session's ~15s-interval polling and
# this app already runs as a single uvicorn process (same tradeoff as the extension's
# live-connection state elsewhere in this codebase). Upgrade to a DB-backed window if this ever
# runs multi-worker.
_recent_candidates: dict[int, deque] = {}


def _record_candidate(session_id: int, is_candidate: bool) -> bool:
    """Appends this poll's candidate flag to the session's rolling window and reports whether
    it's now corroborated. Pure bookkeeping, no model inference - kept separate so it's testable
    without loading YOLO."""
    window = _recent_candidates.setdefault(session_id, deque(maxlen=CANDIDATE_WINDOW_SIZE))
    window.append(is_candidate)
    return sum(window) >= CANDIDATE_CORROBORATION_COUNT

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

        # Predict at the lower candidate threshold so weak-but-real detections aren't discarded
        # before they get a chance to be corroborated across polls.
        phone_results = _PHONE_MODEL.predict(
            image, verbose=False, conf=PHONE_CANDIDATE_THRESHOLD
        )[0]
        if phone_results.boxes is not None:
            phone_scores = [
                conf for conf, cls in zip(phone_results.boxes.conf.tolist(), phone_results.boxes.cls.tolist())
                if cls == PHONE_SPECIALIST_CLASS
            ]
        else:
            phone_scores = []
        max_phone_conf = max(phone_scores, default=0.0)

        phone_detected = max_phone_conf >= PHONE_SPECIALIST_CONFIDENCE_THRESHOLD
        is_candidate = max_phone_conf >= PHONE_CANDIDATE_THRESHOLD
        corroborated = _record_candidate(session_id, is_candidate)

        if not phone_detected:
            pose_results = _POSE_MODEL.predict(image, verbose=False)[0]
            phone_detected = _phone_near_hands(image, pose_results) or corroborated

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


if __name__ == "__main__":
    # Self-check for the corroboration bookkeeping only - no YOLO models involved.
    _recent_candidates.clear()
    assert _record_candidate(1, False) is False
    assert _record_candidate(1, True) is False, "one candidate hit alone shouldn't corroborate"
    assert _record_candidate(1, True) is True, "second candidate hit within the window should corroborate"
    # A fresh session's window is independent of session 1's.
    assert _record_candidate(2, True) is False
    # Window is a rolling maxlen - once full, a new poll evicts the oldest and an old hit ages out.
    _recent_candidates[3] = deque([True, False, False], maxlen=CANDIDATE_WINDOW_SIZE)
    assert _record_candidate(3, False) is False, "the lone True should have aged out by now"
    print("object_detection_service self-check passed")
