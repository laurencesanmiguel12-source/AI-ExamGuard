"""Empirical threshold analysis for face identity verification (face_service.py's
CONFIDENCE_THRESHOLD = 80.0, LBPH distance-based matching). This threshold has never been
validated against real data - every other threshold in this codebase's proctoring pipeline
(phone confidence, hand-crop size, head-down pitch/duration/miss-tolerance, pose-fallback
confidence) has an empirical sweep behind it; this one is still the original guessed default.

Real enrolled students' raw photos are never persisted (see FaceService.enroll - only the trained
.yml model is kept, by design, for privacy), so there's no stored image set of real enrolled
faces to build genuine/impostor pairs from directly. Uses the same real-data-proxy approach
already established for the phone/head-pose work: backend/training/datasets/oep-msu/
annotation_batch's 11 subjects (real webcam footage, real people, real lighting variety) stand in
for "enrolled students" - for each subject, a handful of their own frames are used to train an
LBPH model exactly the way FaceService.enroll does, held-out frames from the SAME subject are
"genuine" verification attempts, and frames from every OTHER subject are "impostor" attempts.

Runs the real production detect+crop pipeline (face_service._detect_largest_face /
_crop_from_detection) on every frame - a frame YuNet fails to detect a face in is skipped, same
as what would happen in production (no crop, no recognition attempt).

Output: printed genuine/impostor confidence distributions, then a precision/recall/FAR/FRR sweep
across candidate thresholds, same reporting shape as threshold_sweep.py's phone-confidence work.
"""
import glob
import os
import random
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services.face_service import (  # noqa: E402
    CONFIDENCE_THRESHOLD,
    _crop_from_detection,
    _detect_largest_face,
)

DATASET_DIR = os.path.join(os.path.dirname(__file__), "datasets", "oep-msu", "annotation_batch")
SUBJECTS = [
    "subject01", "subject02", "subject03", "subject04", "subject06",
    "subject09", "subject10", "subject11", "subject12", "subject13", "subject24",
]

ENROLLMENT_SAMPLES = 5  # matches FaceEnrollment.jsx's TARGET_CAPTURES default
MAX_GENUINE_TEST_PER_SUBJECT = 30
MAX_IMPOSTOR_TEST_PER_FOREIGN_SUBJECT = 5
SEED = 20260808


def _crops_for_subject(subject: str) -> list:
    """Runs the real detect+crop pipeline on every one of a subject's frames, in a fixed
    shuffled order. Frames YuNet can't find a face in are silently skipped, same as
    production - this is deliberately NOT gated on the dataset's own face-box label, so a
    detector failure here counts against this subject's usable sample count exactly like it
    would in the real app."""
    paths = sorted(glob.glob(os.path.join(DATASET_DIR, f"{subject}_*.jpg")))
    rng = random.Random(SEED)
    rng.shuffle(paths)

    crops = []
    for path in paths:
        image = cv2.imread(path)
        if image is None:
            continue
        detection = _detect_largest_face(image)
        if detection is None:
            continue
        crop = _crop_from_detection(image, detection)
        if crop is not None:
            crops.append(crop)
    return crops


def main():
    print(f"Loading + detecting faces for {len(SUBJECTS)} subjects (real YuNet pipeline, this takes a bit)...")
    per_subject_crops = {s: _crops_for_subject(s) for s in SUBJECTS}
    for s, crops in per_subject_crops.items():
        print(f"  {s}: {len(crops)} usable face crops")

    usable = {s: c for s, c in per_subject_crops.items() if len(c) >= ENROLLMENT_SAMPLES + 3}
    skipped = set(SUBJECTS) - set(usable)
    if skipped:
        print(f"Skipping (too few usable crops for enrollment + a real test set): {sorted(skipped)}")

    enrollment = {}
    genuine_test = {}
    for s, crops in usable.items():
        enrollment[s] = crops[:ENROLLMENT_SAMPLES]
        genuine_test[s] = crops[ENROLLMENT_SAMPLES:ENROLLMENT_SAMPLES + MAX_GENUINE_TEST_PER_SUBJECT]

    print("\nTraining one LBPH model per subject (exactly FaceService.enroll's own training call)...")
    models = {}
    for s, samples in enrollment.items():
        recognizer = cv2.face.LBPHFaceRecognizer_create()
        labels = np.array([0] * len(samples))  # single-class per model, same as real enrollment
        recognizer.train(samples, labels)
        models[s] = recognizer

    genuine_confidences = []
    impostor_confidences = []

    for s, recognizer in models.items():
        for crop in genuine_test[s]:
            _, confidence = recognizer.predict(crop)
            genuine_confidences.append(confidence)

        for other in usable:
            if other == s:
                continue
            for crop in genuine_test[other][:MAX_IMPOSTOR_TEST_PER_FOREIGN_SUBJECT]:
                _, confidence = recognizer.predict(crop)
                impostor_confidences.append(confidence)

    genuine_confidences.sort()
    impostor_confidences.sort()

    def _stats(values):
        n = len(values)
        return (
            f"n={n}, min={values[0]:.1f}, median={values[n // 2]:.1f}, "
            f"max={values[-1]:.1f}"
        )

    print(f"\nGenuine (same-person) confidence distribution: {_stats(genuine_confidences)}")
    print(f"Impostor (different-person) confidence distribution: {_stats(impostor_confidences)}")
    print("(LBPH confidence is a DISTANCE - lower means more similar to the enrolled model)")

    def _metrics_at(threshold: float) -> dict:
        tp = sum(1 for c in genuine_confidences if c < threshold)
        fn = len(genuine_confidences) - tp
        fp = sum(1 for c in impostor_confidences if c < threshold)
        tn = len(impostor_confidences) - fp

        precision = tp / (tp + fp) if (tp + fp) else float("nan")
        recall = tp / (tp + fn) if (tp + fn) else float("nan")
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else float("nan")
        far = fp / (fp + tn) if (fp + tn) else float("nan")  # impostor wrongly accepted
        frr = fn / (fn + tp) if (fn + tp) else float("nan")  # genuine wrongly rejected
        return {"precision": precision, "recall": recall, "f1": f1, "far": far, "frr": frr}

    print(f"\n{'Threshold':>10} {'Precision':>10} {'Recall':>8} {'F1':>6} {'FAR':>6} {'FRR':>6}")
    lo = int(min(genuine_confidences[0], impostor_confidences[0]) // 5 * 5)
    hi = int(max(genuine_confidences[-1], impostor_confidences[-1]) // 5 * 5 + 5)
    best_f1, best_threshold = -1.0, None
    current_metrics = None
    for threshold in range(lo, hi + 1, 5):
        m = _metrics_at(float(threshold))
        marker = " <- current CONFIDENCE_THRESHOLD" if threshold == int(CONFIDENCE_THRESHOLD) else ""
        print(
            f"{threshold:>10} {m['precision']:>10.3f} {m['recall']:>8.3f} "
            f"{m['f1']:>6.3f} {m['far']:>6.3f} {m['frr']:>6.3f}{marker}"
        )
        if threshold == int(CONFIDENCE_THRESHOLD):
            current_metrics = m
        if m["f1"] > best_f1:
            best_f1, best_threshold = m["f1"], threshold

    print(f"\nCurrent CONFIDENCE_THRESHOLD={CONFIDENCE_THRESHOLD}: {current_metrics}")
    print(f"F1-optimal on this data: threshold={best_threshold}, F1={best_f1:.3f}")
    print(
        "\nNOT a recommendation to switch blindly - per this project's own threshold_sweep "
        "history (phone confidence), a holdout-optimal value still needs a live smoke-test "
        "across real hardware/lighting before shipping."
    )


if __name__ == "__main__":
    main()
