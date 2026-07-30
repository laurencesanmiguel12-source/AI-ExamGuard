"""One-time final-comparison evaluation against datasets/oep-msu/frozen_holdout/ - see
make_frozen_holdout.py's docstring for why this set exists and, critically, when NOT to use it.

**Do not run this mid-development.** Use the ordinary subject09/11 val split (already wired into
every finetune_phone_face.py run) for iterating - picking checkpoints, comparing epochs, deciding
whether a training run is worth finishing. Only reach for this script once, per candidate model,
when writing up a real "should this replace production" comparison, and report whatever it says
even if unflattering. Running it more than once per candidate and picking the best result defeats
the entire point.

Reports frame-level phone-detection outcomes at the app's real production confidence threshold
(PHONE_SPECIALIST_CONFIDENCE_THRESHOLD below - copied from object_detection_service.py rather than
imported, same convention as the annotate_phone_backface_live_review*.py scripts, since importing
that module directly would pull in the live app's SQLAlchemy models/DB config, which these
standalone training scripts intentionally don't depend on. Keep this value in sync by hand if the
service's threshold ever changes): for every frame, "phone visible" ground truth
comes from whether frozen_holdout/<frame>.txt has a class-0 box; "phone detected" comes from whether
the candidate model's own prediction has a class-0 box at or above that threshold. IoU against the
ground-truth box is also checked (--iou-thresh, default 0.3 - looser than the usual 0.5 since these
ground-truth boxes are manual visual estimates, not pixel-exact) so a correct-by-luck detection in
the wrong part of the frame doesn't count as a hit.

Usage:
  ../.venv/Scripts/python.exe evaluate_frozen_holdout.py --model ../app/resources/phone_specialist.pt
  ../.venv/Scripts/python.exe evaluate_frozen_holdout.py --model runs/phone_face_specialist-6/weights/best.pt
"""
import argparse
import os

import cv2
from ultralytics import YOLO

# Copied from app/services/object_detection_service.py (see docstring above for why this isn't a
# direct import) - keep in sync by hand if the service's threshold ever changes.
PHONE_SPECIALIST_CONFIDENCE_THRESHOLD = 0.35
PHONE_SPECIALIST_CLASS = 0

HOLDOUT_DIR = os.path.join(os.path.dirname(__file__), "datasets", "oep-msu", "frozen_holdout")


def load_gt_phone_box(label_path, img_w, img_h):
    if not os.path.exists(label_path):
        return None
    with open(label_path) as f:
        for line in f:
            parts = line.split()
            if int(parts[0]) != PHONE_SPECIALIST_CLASS:
                continue
            cx, cy, w, h = (float(v) for v in parts[1:5])
            x1 = (cx - w / 2) * img_w
            y1 = (cy - h / 2) * img_h
            x2 = (cx + w / 2) * img_w
            y2 = (cy + h / 2) * img_h
            return (x1, y1, x2, y2)
    return None


def iou(box_a, box_b):
    ax1, ay1, ax2, ay2 = box_a
    bx1, by1, bx2, by2 = box_b
    ix1, iy1 = max(ax1, bx1), max(ay1, by1)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    iw, ih = max(0.0, ix2 - ix1), max(0.0, iy2 - iy1)
    inter = iw * ih
    area_a = (ax2 - ax1) * (ay2 - ay1)
    area_b = (bx2 - bx1) * (by2 - by1)
    union = area_a + area_b - inter
    return inter / union if union > 0 else 0.0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True)
    parser.add_argument("--iou-thresh", type=float, default=0.3)
    args = parser.parse_args()

    if not os.path.isdir(HOLDOUT_DIR) or not os.listdir(HOLDOUT_DIR):
        print(f"{HOLDOUT_DIR} is empty - run make_frozen_holdout.py first.")
        return

    model = YOLO(args.model)
    image_files = sorted(f for f in os.listdir(HOLDOUT_DIR) if f.lower().endswith(".jpg"))

    tp = fp = fn = tn = 0
    localization_misses = 0  # detected phone-present correctly, but box didn't overlap ground truth

    for fname in image_files:
        img_path = os.path.join(HOLDOUT_DIR, fname)
        label_path = os.path.join(HOLDOUT_DIR, os.path.splitext(fname)[0] + ".txt")
        image = cv2.imread(img_path)
        h, w = image.shape[:2]

        gt_box = load_gt_phone_box(label_path, w, h)

        result = model.predict(image, verbose=False, conf=PHONE_SPECIALIST_CONFIDENCE_THRESHOLD)[0]
        pred_boxes = [
            tuple(float(v) for v in box.xyxy[0])
            for box in result.boxes
            if int(box.cls[0]) == PHONE_SPECIALIST_CLASS
        ]

        if gt_box is None:
            if pred_boxes:
                fp += 1
            else:
                tn += 1
        else:
            if not pred_boxes:
                fn += 1
            else:
                best_iou = max(iou(gt_box, pb) for pb in pred_boxes)
                if best_iou >= args.iou_thresh:
                    tp += 1
                else:
                    localization_misses += 1
                    fn += 1

    n = len(image_files)
    precision = tp / (tp + fp) if (tp + fp) else float("nan")
    recall = tp / (tp + fn) if (tp + fn) else float("nan")
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else float("nan")

    print(f"model: {args.model}")
    print(f"frozen holdout: {n} frames ({tp + fn} phone-positive, {tn + fp} phone-negative)")
    print(f"confidence threshold: {PHONE_SPECIALIST_CONFIDENCE_THRESHOLD}  iou threshold: {args.iou_thresh}")
    print(f"TP={tp} FP={fp} FN={fn} TN={tn}  (of which {localization_misses} FN were 'detected a phone "
          f"somewhere, but not overlapping the real one')")
    print(f"precision={precision:.3f} recall={recall:.3f} f1={f1:.3f}")


if __name__ == "__main__":
    main()
