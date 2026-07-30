"""One-time final-comparison evaluation against datasets/oep-msu/frozen_holdout/ - see
make_frozen_holdout.py's docstring for why this set exists and, critically, when NOT to use it.

**Do not run this mid-development.** Use the ordinary subject09/11 val split (already wired into
every finetune_phone_face.py run) for iterating - picking checkpoints, comparing epochs, deciding
whether a training run is worth finishing. Only reach for this script once, per candidate model,
when writing up a real "should this replace production" comparison, and report whatever it says
even if unflattering. Running it more than once per candidate and picking the best result defeats
the entire point.

Runs the FULL production pipeline (whole-frame phone_specialist pass + pose-guided hand-crop
fallback, both matching object_detection_service.py exactly - see eval_common.py's docstring) at the
app's real confidence thresholds, and reports two numbers: "presence" (matches production's actual
`phone_detected = PHONE_SPECIALIST_CLASS in phone_classes` check exactly - no location awareness,
which is what really drives a violation being logged) and "localized" (additionally IoU-gates
against the real ground-truth box - a model-quality diagnostic, not what production itself checks).
Report the presence number as the real comparison; use localized to sanity-check the model isn't
getting the right answer for the wrong reason.

Usage:
  ../.venv/Scripts/python.exe evaluate_frozen_holdout.py --model ../app/resources/phone_specialist.pt
  ../.venv/Scripts/python.exe evaluate_frozen_holdout.py --model runs/phone_face_specialist-6/weights/best.pt
"""
import argparse
import os

import cv2
from ultralytics import YOLO

from eval_common import analyze_frame, load_gt_phone_box

HOLDOUT_DIR = os.path.join(os.path.dirname(__file__), "datasets", "oep-msu", "frozen_holdout")
POSE_MODEL_PATH = os.path.join(os.path.dirname(__file__), "..", "app", "resources", "yolov8n-pose.pt")

# Copied from app/services/object_detection_service.py, same convention as elsewhere in this
# project - keep in sync by hand if the service's threshold ever changes.
PHONE_SPECIALIST_CONFIDENCE_THRESHOLD = 0.70


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True)
    parser.add_argument("--iou-thresh", type=float, default=0.3)
    parser.add_argument("--device", default="cpu")
    args = parser.parse_args()

    if not os.path.isdir(HOLDOUT_DIR) or not os.listdir(HOLDOUT_DIR):
        print(f"{HOLDOUT_DIR} is empty - run make_frozen_holdout.py first.")
        return

    phone_model = YOLO(args.model)
    pose_model = YOLO(POSE_MODEL_PATH)
    image_files = sorted(f for f in os.listdir(HOLDOUT_DIR) if f.lower().endswith(".jpg"))

    tp_p = fp_p = tp_l = fp_l = 0
    total_gt = 0
    wrong_reason = 0  # presence-hit but not localized: right verdict, box didn't match real phone

    for fname in image_files:
        img_path = os.path.join(HOLDOUT_DIR, fname)
        label_path = os.path.join(HOLDOUT_DIR, os.path.splitext(fname)[0] + ".txt")
        image = cv2.imread(img_path)
        h, w = image.shape[:2]
        gt_box = load_gt_phone_box(label_path, w, h)
        has_gt = gt_box is not None
        if has_gt:
            total_gt += 1

        r = analyze_frame(image, gt_box, phone_model, pose_model, PHONE_SPECIALIST_CONFIDENCE_THRESHOLD,
                           args.iou_thresh, args.device)
        presence_hit = (r["max_conf_any"] >= PHONE_SPECIALIST_CONFIDENCE_THRESHOLD) or r["fallback_hit"]
        localized_hit = (
            (r["best_match_conf"] is not None and r["best_match_conf"] >= PHONE_SPECIALIST_CONFIDENCE_THRESHOLD)
            or (r["fallback_hit"] and r["fallback_matched_gt"])
        )

        if has_gt:
            tp_p += int(presence_hit)
            tp_l += int(bool(localized_hit))
            if presence_hit and not localized_hit:
                wrong_reason += 1
        else:
            fp_p += int(presence_hit)
            fp_l += int(presence_hit)

    n = len(image_files)
    fn_p, fn_l = total_gt - tp_p, total_gt - tp_l
    prec_p = tp_p / (tp_p + fp_p) if (tp_p + fp_p) else float("nan")
    rec_p = tp_p / total_gt if total_gt else float("nan")
    f1_p = 2 * prec_p * rec_p / (prec_p + rec_p) if prec_p == prec_p and (prec_p + rec_p) else float("nan")
    prec_l = tp_l / (tp_l + fp_l) if (tp_l + fp_l) else float("nan")
    rec_l = tp_l / total_gt if total_gt else float("nan")
    f1_l = 2 * prec_l * rec_l / (prec_l + rec_l) if prec_l == prec_l and (prec_l + rec_l) else float("nan")

    print(f"model: {args.model}")
    print(f"frozen holdout: {n} frames ({total_gt} phone-positive, {n - total_gt} phone-negative)")
    print(f"confidence threshold: {PHONE_SPECIALIST_CONFIDENCE_THRESHOLD}  iou threshold: {args.iou_thresh}")
    print(f"presence  (real production behavior): TP={tp_p} FP={fp_p} FN={fn_p}  "
          f"precision={prec_p:.3f} recall={rec_p:.3f} f1={f1_p:.3f}")
    print(f"localized (diagnostic, IoU-gated):     TP={tp_l} FP={fp_l} FN={fn_l}  "
          f"precision={prec_l:.3f} recall={rec_l:.3f} f1={f1_l:.3f}")
    print(f"{wrong_reason} phone-positive frames were flagged correctly but NOT via a box overlapping "
          f"the real phone (right verdict, wrong reason - worth a look if this number is large)")


if __name__ == "__main__":
    main()
