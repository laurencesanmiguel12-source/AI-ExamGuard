"""Evaluate a phone model against the held-out new_video people (p4, p5 - never in training),
running the FULL production pipeline (whole-frame phone_specialist pass + pose-guided hand-crop
fallback + face-anchored IoU suppression) at the real 0.35 threshold, same as
evaluate_frozen_holdout.py / eval_common.py.

Why this exists: the frozen_holdout has zero lighting/hardware diversity within a single
phone/session (see ai_examguard_frozen_holdout_eval - the 0.70-threshold live-recall crash it
missed). This set is 2 unseen people on their own real webcams. It is almost entirely
phone-POSITIVE (363/365 frames), so it measures RECALL/generalization, not precision - use the
frozen_holdout's 226 negatives for the precision/FP regression check, and this for "does it still
find real phones on hardware it's never seen." Run once per candidate, report the number.

Usage:
  ../.venv/Scripts/python.exe evaluate_new_video_holdout.py --model ../app/resources/phone_specialist.pt
  ../.venv/Scripts/python.exe evaluate_new_video_holdout.py --model runs/phone_face_specialist-13/weights/best.pt
"""
import argparse
import os

import cv2
from ultralytics import YOLO

from eval_common import analyze_frame, load_gt_phone_boxes

HOLDOUT_DIR = os.path.join(os.path.dirname(__file__), "datasets", "new_video", "holdout")
POSE_MODEL_PATH = os.path.join(os.path.dirname(__file__), "..", "app", "resources", "yolov8n-pose.pt")
PHONE_SPECIALIST_CONFIDENCE_THRESHOLD = 0.35  # keep in sync with object_detection_service.py


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True)
    parser.add_argument("--iou-thresh", type=float, default=0.3)
    parser.add_argument("--device", default="cpu")
    args = parser.parse_args()

    img_dir = os.path.join(HOLDOUT_DIR, "images")
    lbl_dir = os.path.join(HOLDOUT_DIR, "labels")
    if not os.path.isdir(img_dir):
        print(f"{img_dir} missing - run build_new_video_dataset.py first.")
        return

    phone_model = YOLO(args.model)
    pose_model = YOLO(POSE_MODEL_PATH)
    files = sorted(f for f in os.listdir(img_dir) if f.lower().endswith(".jpg"))

    tp = fp = fn = 0
    total_gt = 0
    per_person = {}
    for fname in files:
        person = fname.split("_")[0]
        image = cv2.imread(os.path.join(img_dir, fname))
        h, w = image.shape[:2]
        gt_boxes = load_gt_phone_boxes(os.path.join(lbl_dir, os.path.splitext(fname)[0] + ".txt"), w, h)
        has_gt = bool(gt_boxes)
        if has_gt:
            total_gt += 1

        r = analyze_frame(image, gt_boxes, phone_model, pose_model,
                          PHONE_SPECIALIST_CONFIDENCE_THRESHOLD, args.iou_thresh, args.device)
        hit = (r["max_conf_any"] >= PHONE_SPECIALIST_CONFIDENCE_THRESHOLD) or r["fallback_hit"]

        pp = per_person.setdefault(person, {"gt": 0, "tp": 0, "fp": 0})
        if has_gt:
            pp["gt"] += 1
            tp += hit
            fn += (not hit)
            pp["tp"] += hit
        else:
            fp += hit
            pp["fp"] += hit

    recall = tp / total_gt if total_gt else float("nan")
    print(f"model: {args.model}")
    print(f"new_video holdout: {len(files)} frames, {total_gt} phone-positive, "
          f"{len(files) - total_gt} negative  (threshold {PHONE_SPECIALIST_CONFIDENCE_THRESHOLD})")
    print(f"presence recall on real phones: {recall:.3f}  (TP={tp} FN={fn}); FP on negatives={fp}")
    for person, pp in sorted(per_person.items()):
        r = pp["tp"] / pp["gt"] if pp["gt"] else float("nan")
        print(f"  {person}: recall {r:.3f} ({pp['tp']}/{pp['gt']})  FP={pp['fp']}")


if __name__ == "__main__":
    main()
