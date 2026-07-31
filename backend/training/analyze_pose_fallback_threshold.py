"""Empirical validation for _HEAD_PRESENCE_CONFIDENCE_THRESHOLD (face_service.py), the last
unvalidated head-down-detection threshold - see the gaze-monitoring feasibility memory. It was
borrowed from object_detection_service.py's WRIST_VISIBILITY_THRESHOLD (swept for the *wrist*
keypoint on this same pose model, not the nose), so this checks it against real data instead of
leaving it as a borrowed guess.

Ground truth: annotation_batch's human-labeled "face" class (index 1 in classes.txt) - present in
2200/2222 frames, independent of phone visibility. Restricted to the frames that actually matter
for this code path: only where YuNet itself already failed to find a face (the fallback never
runs otherwise), so precision/recall here reflects the fallback's actual operating conditions,
not the full dataset.
"""
import glob
import os
import sys

import cv2

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services.face_service import _detect_largest_face, _NOSE_KPT  # noqa: E402
from app.services.object_detection_service import _POSE_MODEL  # noqa: E402

BATCH_DIR = os.path.join(os.path.dirname(__file__), "datasets", "oep-msu", "annotation_batch")


def has_face_label(label_path: str) -> bool:
    if not os.path.exists(label_path):
        return False
    with open(label_path) as f:
        classes = [line.split()[0] for line in f if line.strip()]
    return "1" in classes


def nose_confidence(image) -> float:
    """Max nose-keypoint confidence across all detected people in frame (0.0 if none)."""
    pose_results = _POSE_MODEL.predict(image, verbose=False)[0]
    if pose_results.keypoints is None or len(pose_results.keypoints.data) == 0:
        return 0.0
    return max(
        float(person_kpts[_NOSE_KPT][2])
        for person_kpts in pose_results.keypoints.data
    )


def main():
    jpgs = sorted(glob.glob(os.path.join(BATCH_DIR, "*.jpg")))
    print(f"Found {len(jpgs)} frames - filtering to YuNet-failed subset "
          f"(only where the fallback actually runs)...")

    rows = []
    for i, jpg_path in enumerate(jpgs):
        label_path = jpg_path[:-4] + ".txt"
        if not os.path.exists(label_path):
            continue

        image = cv2.imread(jpg_path)
        if image is None:
            continue

        detection = _detect_largest_face(image)
        if detection is not None:
            continue  # YuNet succeeded - fallback never runs for this frame in production

        rows.append({
            "file": os.path.basename(jpg_path),
            "has_face_label": has_face_label(label_path),
            "nose_confidence": nose_confidence(image),
        })

        if len(rows) % 50 == 0:
            print(f"  {len(rows)} YuNet-failed frames processed so far ({i + 1}/{len(jpgs)} scanned)")

    print(f"\nYuNet-failed subset: {len(rows)} frames")
    face_labeled = sum(1 for r in rows if r["has_face_label"])
    print(f"  of those, {face_labeled} have a human-labeled face (real head-present-but-YuNet-missed-it), "
          f"{len(rows) - face_labeled} have no face label (genuinely no one there)")

    print(f"\n{'threshold':>10} {'precision':>10} {'recall':>8} {'f1':>6} {'flagged':>8} {'tp':>5} {'fp':>5} {'fn':>5}")
    for threshold in [0.02, 0.05, 0.08, 0.10, 0.15, 0.20, 0.30, 0.40, 0.50]:
        tp = sum(1 for r in rows if r["nose_confidence"] >= threshold and r["has_face_label"])
        fp = sum(1 for r in rows if r["nose_confidence"] >= threshold and not r["has_face_label"])
        fn = sum(1 for r in rows if r["nose_confidence"] < threshold and r["has_face_label"])
        flagged = tp + fp
        precision = tp / flagged if flagged else 0
        recall = tp / (tp + fn) if (tp + fn) else 0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0
        print(f"{threshold:>10} {precision:>10.3f} {recall:>8.3f} {f1:>6.3f} {flagged:>8} {tp:>5} {fp:>5} {fn:>5}")


if __name__ == "__main__":
    main()
