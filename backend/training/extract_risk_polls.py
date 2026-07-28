"""Run AI ExamGuard's real face/phone/person detectors over the MSU OEP dataset's already-extracted
webcam frames (datasets/oep-msu/raw_frames/, see extract_oep_frames.py), sampled at
POLL_INTERVAL_SECONDS to match ExamRoom's live polling cadence, and cache the raw per-poll results
to datasets/risk-oep/polls.csv.

Split out from labeling (see build_risk_windows.py) because detection is the slow, expensive part
(~1s/poll on CPU across 3 YOLO passes + YuNet) while how gt.txt timestamps get turned into window
labels is a much faster judgment call worth iterating on without re-running inference every time.

Usage: ../../.venv/Scripts/python.exe extract_risk_polls.py
"""
import csv
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services import face_service, object_detection_service  # noqa: E402

FRAMES_DIR = os.path.join(os.path.dirname(__file__), "datasets", "oep-msu", "raw_frames")
OUT_DIR = os.path.join(os.path.dirname(__file__), "datasets", "risk-oep")
OUT_CSV = os.path.join(OUT_DIR, "polls.csv")

POLL_INTERVAL_SECONDS = 15  # matches ExamRoom's live face/phone-check polling cadence

FIELDNAMES = ["subject", "time_sec", "face_lost", "phone_detected", "person_count"]


def detect_poll(image_bytes):
    face_crop = face_service._detect_and_crop(image_bytes)
    face_lost = face_crop is None

    image = object_detection_service._decode(image_bytes)
    if image is None:
        return face_lost, False, 0

    results = object_detection_service._MODEL.predict(
        image, verbose=False, conf=object_detection_service.CONFIDENCE_THRESHOLD
    )[0]
    classes = results.boxes.cls.tolist() if results.boxes is not None else []
    person_count = classes.count(object_detection_service.PERSON_CLASS)

    phone_results = object_detection_service._PHONE_MODEL.predict(
        image, verbose=False, conf=object_detection_service.PHONE_SPECIALIST_CONFIDENCE_THRESHOLD
    )[0]
    phone_classes = phone_results.boxes.cls.tolist() if phone_results.boxes is not None else []
    phone_detected = object_detection_service.PHONE_SPECIALIST_CLASS in phone_classes

    if not phone_detected:
        pose_results = object_detection_service._POSE_MODEL.predict(image, verbose=False)[0]
        phone_detected = object_detection_service._phone_near_hands(image, pose_results)

    return face_lost, phone_detected, person_count


def process_subject(subject_dir_name):
    frame_dir = os.path.join(FRAMES_DIR, subject_dir_name)
    frame_files = sorted(f for f in os.listdir(frame_dir) if f.endswith(".jpg"))

    polls = []
    for i, fname in enumerate(frame_files):
        t = i  # raw_frames extracted at 1fps, so frame index == second offset
        if t % POLL_INTERVAL_SECONDS != 0:
            continue
        with open(os.path.join(frame_dir, fname), "rb") as f:
            image_bytes = f.read()
        face_lost, phone_detected, person_count = detect_poll(image_bytes)
        polls.append({
            "subject": subject_dir_name,
            "time_sec": t,
            "face_lost": int(face_lost),
            "phone_detected": int(phone_detected),
            "person_count": person_count,
        })
    return polls


def main():
    if not os.path.isdir(FRAMES_DIR):
        raise SystemExit(f"{FRAMES_DIR} not found - run extract_oep_frames.py first.")

    os.makedirs(OUT_DIR, exist_ok=True)

    subject_dirs = sorted(d for d in os.listdir(FRAMES_DIR) if d.startswith("subject"))

    all_polls = []
    for subject_dir in subject_dirs:
        polls = process_subject(subject_dir)
        print(f"{subject_dir}: {len(polls)} polls")
        all_polls.extend(polls)

    with open(OUT_CSV, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(all_polls)

    print(f"\n{len(all_polls)} polls across {len(subject_dirs)} subjects -> {OUT_CSV}")


if __name__ == "__main__":
    main()
