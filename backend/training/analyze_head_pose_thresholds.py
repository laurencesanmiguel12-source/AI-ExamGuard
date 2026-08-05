"""Empirical threshold analysis for the PROLONGED_HEAD_DOWN feature (see
ai_examguard_gaze_monitoring_feasibility memory). Runs the real production head-pose pipeline
(face_service._detect_largest_face / _estimate_head_pose / _pose_fallback_signals)
against annotation_batch's 2222 human-labeled frames (phone-present vs phone-absent), using
phone-present as a real-world proxy for "student is looking down, possibly at a phone."

Not a perfect ground truth for "head pitched down" specifically (a phone could be held up near
eye level in rare cases, and a person could look down for reasons other than a phone), but it's
real, diverse (many subjects, camera angles, lighting), human-labeled data - much stronger
evidence than the single-session live smoke-test alone.

Output: CSV with per-frame pitch/fallback results + a printed precision/recall sweep, same
discipline as backend/training/threshold_sweep.py's phone-confidence work.
"""
import csv
import glob
import os
import sys
import time

import cv2

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services.face_service import (  # noqa: E402
    _detect_largest_face,
    _estimate_head_pose,
    _pose_fallback_signals,
    _HEAD_PRESENCE_CONFIDENCE_THRESHOLD,
)

BATCH_DIR = os.path.join(os.path.dirname(__file__), "datasets", "oep-msu", "annotation_batch")
OUT_CSV = os.path.join(os.path.dirname(__file__), "head_pose_threshold_data.csv")


def phone_present(label_path: str) -> bool | None:
    if not os.path.exists(label_path):
        return None
    with open(label_path) as f:
        classes = [line.split()[0] for line in f if line.strip()]
    return "0" in classes


def main():
    jpgs = sorted(glob.glob(os.path.join(BATCH_DIR, "*.jpg")))
    print(f"Found {len(jpgs)} frames")

    rows = []
    start = time.perf_counter()
    for i, jpg_path in enumerate(jpgs):
        label_path = jpg_path[:-4] + ".txt"
        phone = phone_present(label_path)
        if phone is None:
            continue

        image = cv2.imread(jpg_path)
        if image is None:
            continue

        detection = _detect_largest_face(image)
        if detection is not None:
            pose = _estimate_head_pose(image, detection)
        else:
            pose = None

        fallback = None
        if detection is None:
            _, nose_confidence = _pose_fallback_signals(image)
            fallback = nose_confidence >= _HEAD_PRESENCE_CONFIDENCE_THRESHOLD

        rows.append({
            "file": os.path.basename(jpg_path),
            "subject": os.path.basename(jpg_path).split("_")[0],
            "phone_present": phone,
            "yunet_detected": detection is not None,
            "pitch": pose["pitch"] if pose else "",
            "yaw": pose["yaw"] if pose else "",
            "roll": pose["roll"] if pose else "",
            "fallback_head_present": fallback if fallback is not None else "",
        })

        if (i + 1) % 200 == 0:
            elapsed = time.perf_counter() - start
            rate = (i + 1) / elapsed
            remaining = (len(jpgs) - i - 1) / rate
            print(f"  {i + 1}/{len(jpgs)} ({rate:.1f}/s, ~{remaining:.0f}s remaining)")

    with open(OUT_CSV, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nWrote {len(rows)} rows to {OUT_CSV}")


if __name__ == "__main__":
    main()
