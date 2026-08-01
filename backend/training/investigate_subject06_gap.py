"""Investigate subject06's persistent recall gap (recall 0.741 vs 0.918 overall in the
2026-08-01 fairness_audit.py re-run against phone_face_specialist-7 - the first per-subject
disparity in this whole audit thread that survived a full retrain on fully-corrected labels, so
it's presumed real rather than a labeling artifact - see ai_examguard_fairness_audit_findings
memory). This doesn't assume why; it measures every subject06 phone-positive frame against the
real deployed pipeline (whole-frame pass + pose-guided hand-crop fallback, matching
object_detection_service.py exactly via eval_common.py) and reports confidence scores for misses,
so a real pattern (near-threshold vs genuinely-zero, clustered by something) can be seen rather
than guessed at.

Usage: ../.venv/Scripts/python.exe investigate_subject06_gap.py
"""
import os

import cv2
from ultralytics import YOLO

from eval_common import PHONE_SPECIALIST_CLASS, analyze_frame, load_gt_phone_boxes  # noqa: F401

BATCH_DIR = os.path.join(os.path.dirname(__file__), "datasets", "oep-msu", "annotation_batch")
HOLDOUT_DIR = os.path.join(os.path.dirname(__file__), "datasets", "oep-msu", "frozen_holdout")
PHONE_MODEL_PATH = os.path.join(os.path.dirname(__file__), "..", "app", "resources", "phone_specialist.pt")
POSE_MODEL_PATH = os.path.join(os.path.dirname(__file__), "..", "app", "resources", "yolov8n-pose.pt")

CONFIDENCE_THRESHOLD = 0.35
IOU_THRESH = 0.3


def collect_subject06_frames():
    frames = []
    for source_dir in (BATCH_DIR, HOLDOUT_DIR):
        if not os.path.isdir(source_dir):
            continue
        for fname in sorted(os.listdir(source_dir)):
            if fname.startswith("subject06") and fname.lower().endswith(".jpg"):
                frames.append(os.path.join(source_dir, fname))
    return frames


def main():
    phone_model = YOLO(PHONE_MODEL_PATH)
    pose_model = YOLO(POSE_MODEL_PATH)

    frames = collect_subject06_frames()
    print(f"{len(frames)} subject06 frames total (phone-positive + negative)")

    rows = []
    for img_path in frames:
        label_path = os.path.splitext(img_path)[0] + ".txt"
        image = cv2.imread(img_path)
        if image is None:
            continue
        h, w = image.shape[:2]
        gt_boxes = load_gt_phone_boxes(label_path, w, h)
        if not gt_boxes:
            continue  # only care about phone-positive frames for a recall investigation

        result = analyze_frame(image, gt_boxes, phone_model, pose_model, conf_floor=0.001,
                                iou_thresh=IOU_THRESH, device="cpu")
        whole_frame_hit = result["max_conf_any"] >= CONFIDENCE_THRESHOLD  # presence: any phone box anywhere
        localized_hit = (result["best_match_conf"] or 0.0) >= CONFIDENCE_THRESHOLD  # box must overlap GT
        production_hit = whole_frame_hit or result["fallback_hit"]  # what the app actually checks
        rows.append({
            "file": os.path.basename(img_path),
            "in_holdout": HOLDOUT_DIR in img_path,
            "max_conf_any": result["max_conf_any"],
            "best_match_conf": result["best_match_conf"],
            "fallback_hit": result["fallback_hit"],
            "whole_frame_hit": whole_frame_hit,
            "localized_hit": localized_hit,
            "hit": production_hit,
        })

    hits = [r for r in rows if r["hit"]]
    misses = [r for r in rows if not r["hit"]]
    whole_frame_only_hits = [r for r in rows if r["whole_frame_hit"]]
    localized_hits = [r for r in rows if r["localized_hit"]]
    fallback_rescued = [r for r in rows if r["hit"] and not r["whole_frame_hit"]]
    mislocalized = [r for r in rows if r["whole_frame_hit"] and not r["localized_hit"]]
    print(f"\n{len(rows)} phone-positive frames, {len(hits)} hit, {len(misses)} missed "
          f"(production recall={len(hits)/len(rows):.3f})")
    print(f"presence recall (any phone box anywhere, no location check): "
          f"{len(whole_frame_only_hits)}/{len(rows)} = {len(whole_frame_only_hits)/len(rows):.3f}")
    print(f"LOCALIZED recall (box must IoU-overlap the real phone - matches fairness_audit.py exactly): "
          f"{len(localized_hits)}/{len(rows)} = {len(localized_hits)/len(rows):.3f}")
    print(f"{len(mislocalized)} frames: model was confident ENOUGH (>=0.35) but boxed the WRONG "
          f"location (mislocalization, not non-detection) - {[r['file'] for r in mislocalized]}")
    print(f"{len(fallback_rescued)} frames were ONLY caught by the pose-guided hand-crop fallback")

    print(f"\n--- Misses, sorted by confidence (near-threshold vs genuinely-zero) ---")
    print(f"{'file':<45} {'max_conf':>9} {'fallback':>9} {'holdout':>8}")
    for r in sorted(misses, key=lambda r: -r["max_conf_any"]):
        print(f"{r['file']:<45} {r['max_conf_any']:>9.3f} {str(r['fallback_hit']):>9} {str(r['in_holdout']):>8}")

    near_threshold = [r for r in misses if r["max_conf_any"] >= 0.15]
    near_zero = [r for r in misses if r["max_conf_any"] < 0.05]
    print(f"\n{len(near_threshold)}/{len(misses)} misses are near-threshold (conf >= 0.15) - "
          f"a calibration/threshold question")
    print(f"{len(near_zero)}/{len(misses)} misses are near-zero confidence (< 0.05) - "
          f"the model genuinely doesn't recognize something about these frames")

    # write miss list for the contact-sheet builder
    out_path = os.path.join(os.path.dirname(__file__), "datasets", "oep-msu", "subject06_gap_misses.txt")
    with open(out_path, "w") as f:
        f.write("\n".join(r["file"] for r in misses) + "\n")
    print(f"\nMiss list written to {out_path}")


if __name__ == "__main__":
    main()
