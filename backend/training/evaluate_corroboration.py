"""Live-smoke-test-equivalent for the temporal corroboration change added to
object_detection_service.py on 2026-08-07 (PHONE_CANDIDATE_THRESHOLD=0.20,
CANDIDATE_WINDOW_SIZE=3, CANDIDATE_CORROBORATION_COUNT=2).

Mirrors the 2026-07-30 threshold-sweep investigation's methodology, which is the reason this
script exists rather than trusting evaluate_frozen_holdout.py alone: that investigation found an
offline aggregate metric (frozen-holdout precision/recall) can look clean while missing a real
failure mode, because a shuffled holdout throws away the fact that real footage arrives as a
*sequence* over time. Corroboration is a sequence-dependent feature - a script that shuffles frames
or treats them independently cannot evaluate it at all. This one replays each real captured batch
in its original filming order (same order the frames were shot, which is the same order
ExamRoom's ~15s polling would have seen them), and reuses eval_common.analyze_frame - the exact
same model calls and fallback logic object_detection_service.py's check() makes - so this measures
the real deployed pipeline's behavior, not a reimplementation of it.

Reports, per batch: OLD (single-frame threshold only, pre-2026-08-07 behavior) vs. NEW
(candidate-threshold + corroboration) recall and false-positive count, plus which specific frames
corroboration recovered or broke. Batches are the four live phone_backface_live_review* captures -
real, sequentially-shot, hand-reviewed footage of exactly the hard back-facing/low-held phone poses
this recall gap is about (see ai_examguard_project_status memory, 2026-07-29/30 entries).

Usage:
  ../.venv/Scripts/python.exe evaluate_corroboration.py
"""
import argparse
import glob
import os

import cv2
from ultralytics import YOLO

from eval_common import analyze_frame, load_gt_phone_boxes

DATASET_ROOT = os.path.join(os.path.dirname(__file__), "datasets", "oep-msu")
PHONE_MODEL_PATH = os.path.join(os.path.dirname(__file__), "..", "app", "resources", "phone_specialist.pt")
POSE_MODEL_PATH = os.path.join(os.path.dirname(__file__), "..", "app", "resources", "yolov8n-pose.pt")

BATCHES = [
    "phone_backface_live_review",
    "phone_backface_live_review2",
    "phone_backface_live_review3",
    "phone_backface_live_review4",
]

# Defaults copied from app/services/object_detection_service.py - keep in sync by hand, same
# convention as PHONE_SPECIALIST_CONFIDENCE_THRESHOLD elsewhere in this file's siblings.
# Overridable via CLI so this script can also be used to sweep alternate corroboration configs.
PHONE_SPECIALIST_CONFIDENCE_THRESHOLD = 0.35


def load_batch(name):
    folder = os.path.join(DATASET_ROOT, name)
    frames = []
    for img_path in sorted(glob.glob(os.path.join(folder, "*.jpg"))):
        label_path = os.path.splitext(img_path)[0] + ".txt"
        frames.append((img_path, label_path))
    return frames


def evaluate_batch(name, phone_model, pose_model, candidate_threshold, window_size, corroboration_count,
                    verbose=True):
    frames = load_batch(name)
    if not frames:
        print(f"skip {name}: no frames found")
        return None

    window = []  # rolling candidate-hit window, replicating _record_candidate's logic inline
    tp_old = fn_old = fp_old = tn_old = 0
    tp_new = fn_new = fp_new = tn_new = 0
    recovered, broke = [], []

    for img_path, label_path in frames:
        image = cv2.imread(img_path)
        if image is None:
            continue
        h, w = image.shape[:2]
        is_positive = bool(load_gt_phone_boxes(label_path, w, h))

        result = analyze_frame(
            image, [], phone_model, pose_model,
            conf_floor=candidate_threshold, iou_thresh=0.3,
        )
        max_conf = result["max_conf_any"]
        fallback_hit = result["fallback_hit"]

        old_detected = max_conf >= PHONE_SPECIALIST_CONFIDENCE_THRESHOLD or fallback_hit

        is_candidate = max_conf >= candidate_threshold
        window.append(is_candidate)
        if len(window) > window_size:
            window.pop(0)
        corroborated = sum(window) >= corroboration_count
        new_detected = old_detected or corroborated

        fname = os.path.basename(img_path)
        if is_positive:
            tp_old += old_detected; fn_old += not old_detected
            tp_new += new_detected; fn_new += not new_detected
            if new_detected and not old_detected:
                recovered.append(fname)
        else:
            fp_old += old_detected; tn_old += not old_detected
            fp_new += new_detected; tn_new += not new_detected
            if new_detected and not old_detected:
                broke.append(fname)

    total_pos = tp_old + fn_old
    total_neg = fp_old + tn_old
    if verbose:
        old_recall = tp_old / total_pos if total_pos else float("nan")
        new_recall = tp_new / total_pos if total_pos else float("nan")
        print(f"\n{name}  ({len(frames)} frames, {total_pos} positive / {total_neg} negative)")
        print(f"  OLD  recall={tp_old}/{total_pos}={old_recall:.1%}   false-positives={fp_old}/{total_neg}")
        print(f"  NEW  recall={tp_new}/{total_pos}={new_recall:.1%}   false-positives={fp_new}/{total_neg}")
        if recovered:
            print(f"  recovered by corroboration ({len(recovered)}): {recovered}")
        if broke:
            print(f"  NEW false positives from corroboration ({len(broke)}): {broke}")

    return {
        "tp_old": tp_old, "fn_old": fn_old, "fp_old": fp_old, "tn_old": tn_old,
        "tp_new": tp_new, "fn_new": fn_new, "fp_new": fp_new, "tn_new": tn_new,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate-threshold", type=float, default=0.20)
    parser.add_argument("--window-size", type=int, default=3)
    parser.add_argument("--corroboration-count", type=int, default=2)
    args = parser.parse_args()

    phone_model = YOLO(PHONE_MODEL_PATH)
    pose_model = YOLO(POSE_MODEL_PATH)

    totals = {"tp_old": 0, "fn_old": 0, "fp_old": 0, "tn_old": 0,
              "tp_new": 0, "fn_new": 0, "fp_new": 0, "tn_new": 0}
    for batch in BATCHES:
        result = evaluate_batch(
            batch, phone_model, pose_model,
            args.candidate_threshold, args.window_size, args.corroboration_count,
        )
        if result:
            for k in totals:
                totals[k] += result[k]

    total_pos = totals["tp_old"] + totals["fn_old"]
    total_neg = totals["fp_old"] + totals["tn_old"]
    print(f"\n=== OVERALL across all batches ({total_pos} positive / {total_neg} negative) ===")
    print(f"  config: candidate_threshold={args.candidate_threshold} "
          f"window={args.window_size} corroboration_count={args.corroboration_count}")
    print(f"  OLD  recall={totals['tp_old']}/{total_pos}={totals['tp_old']/total_pos:.1%}   "
          f"false-positives={totals['fp_old']}/{total_neg}={totals['fp_old']/total_neg:.1%}")
    print(f"  NEW  recall={totals['tp_new']}/{total_pos}={totals['tp_new']/total_pos:.1%}   "
          f"false-positives={totals['fp_new']}/{total_neg}={totals['fp_new']/total_neg:.1%}")


if __name__ == "__main__":
    main()
