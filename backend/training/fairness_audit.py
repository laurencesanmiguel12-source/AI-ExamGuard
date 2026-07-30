"""Tier-1 fairness/bias sensitivity audit (see ai_examguard_thesis_scope_recommendations memory,
priority item #1): a per-subject and per-capture-batch breakdown of the deployed detectors'
accuracy, using whatever real variation already exists across the 11 real OEP subjects and 4
live-capture batches this project has - not a substitute for a genuine demographic audit.

**Real limitation, stated up front, not buried**: the OEP dataset carries no demographic metadata
(no documented skin tone, gender, age, or camera-quality labels - confirmed by checking for any
accompanying documentation, none exists). This script can only report "subjectNN scores X" or
"batch Y scores X" - it cannot say *why* a gap exists (lighting? camera? individual pose habits? a
demographic factor we genuinely can't observe from an anonymized ID?). Any disparity flagged here is
a lead for a real audit (recruit deliberately, label attributes, then re-run this analysis), not a
finished fairness conclusion on its own.

**What this measures**:
- Phone detection: the fine-tuned specialist (phone_specialist.pt by default - the currently
  DEPLOYED model, since this audits what students actually experience, not a training candidate) at
  the app's real production confidence threshold, against the human-reviewed ground-truth boxes
  already in every group's .txt labels. Precision/recall/F1 per group, IoU-matched (same 0.3
  threshold as evaluate_frozen_holdout.py, for the same reason: manual boxes aren't pixel-exact).
- Face detection: the real YuNet detector, re-run fresh against every frame (not reusing the
  labels' own face boxes, even though those also came from YuNet historically - re-running keeps
  this measuring current app behavior, not a frozen snapshot). Reported as detection rate (did YuNet
  find *a* face at all) since every frame has exactly one real person in it - there's no meaningful
  "false positive face" case here, so precision isn't a useful axis for this signal.

Deliberately draws from BOTH annotation_batch/ and frozen_holdout/ (i.e. every real labeled frame
this project has, train and held-out alike) rather than only the holdout - this is a diagnostic
characterization of the deployed model, not a swap decision, so a bigger per-group sample size (for
statistical power to actually detect a disparity) matters more here than avoiding train-set
contamination. Frames drawn from annotation_batch/ DID train the currently-deployed model, so a
group's number there partly reflects "how well did the model memorize this subject," not pure
generalization - noted per-group in the output (train-set groups vs the frozen-holdout-only slice)
so this isn't silently conflated with a genuine holdout number.

Usage: ../.venv/Scripts/python.exe fairness_audit.py [--model ../app/resources/phone_specialist.pt]
"""
import argparse
import os

import cv2
from ultralytics import YOLO

BATCH_DIR = os.path.join(os.path.dirname(__file__), "datasets", "oep-msu", "annotation_batch")
HOLDOUT_DIR = os.path.join(os.path.dirname(__file__), "datasets", "oep-msu", "frozen_holdout")
YUNET_PATH = os.path.join(os.path.dirname(__file__), "..", "app", "resources", "face_detection_yunet_2023mar.onnx")

# Copied from app/services/object_detection_service.py, same convention/reasoning as
# evaluate_frozen_holdout.py - keep in sync by hand.
PHONE_SPECIALIST_CONFIDENCE_THRESHOLD = 0.35
PHONE_SPECIALIST_CLASS = 0
IOU_THRESH = 0.3

GROUP_PREFIXES = (
    "subject01", "subject02", "subject03", "subject04", "subject06", "subject09",
    "subject10", "subject11", "subject12", "subject13", "subject24",
    "backface_capture", "backface_lit2", "backface_100", "backface4",
)


def group_of(fname):
    for prefix in GROUP_PREFIXES:
        if fname.startswith(prefix):
            return prefix
    return None


def load_gt_phone_box(label_path, img_w, img_h):
    if not os.path.exists(label_path):
        return None
    with open(label_path) as f:
        for line in f:
            parts = line.split()
            if int(parts[0]) != PHONE_SPECIALIST_CLASS:
                continue
            cx, cy, w, h = (float(v) for v in parts[1:5])
            x1, y1 = (cx - w / 2) * img_w, (cy - h / 2) * img_h
            x2, y2 = (cx + w / 2) * img_w, (cy + h / 2) * img_h
            return (x1, y1, x2, y2)
    return None


def iou(box_a, box_b):
    ax1, ay1, ax2, ay2 = box_a
    bx1, by1, bx2, by2 = box_b
    ix1, iy1 = max(ax1, bx1), max(ay1, by1)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    inter = max(0.0, ix2 - ix1) * max(0.0, iy2 - iy1)
    union = (ax2 - ax1) * (ay2 - ay1) + (bx2 - bx1) * (by2 - by1) - inter
    return inter / union if union > 0 else 0.0


def collect_frames():
    groups = {}
    for source_dir, in_train in ((BATCH_DIR, True), (HOLDOUT_DIR, False)):
        for fname in sorted(os.listdir(source_dir)):
            if not fname.lower().endswith(".jpg"):
                continue
            g = group_of(fname)
            if g is None:
                continue
            groups.setdefault(g, []).append((os.path.join(source_dir, fname), in_train))
    return groups


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default=os.path.join(
        os.path.dirname(__file__), "..", "app", "resources", "phone_specialist.pt"))
    parser.add_argument("--device", default="cpu",
                         help="defaults to cpu so this doesn't contend with a concurrent GPU training run")
    args = parser.parse_args()

    phone_model = YOLO(args.model)
    face_detector = cv2.FaceDetectorYN_create(YUNET_PATH, "", (320, 320), 0.6, 0.3, 5000)

    groups = collect_frames()

    rows = []
    agg = {"tp": 0, "fp": 0, "fn": 0, "tn": 0, "face_hit": 0, "n": 0}

    for g in sorted(groups):
        frames = groups[g]
        tp = fp = fn = tn = 0
        face_hit = 0
        any_train = any(in_train for _, in_train in frames)
        any_holdout = any(not in_train for _, in_train in frames)

        for img_path, _ in frames:
            image = cv2.imread(img_path)
            h, w = image.shape[:2]
            label_path = os.path.splitext(img_path)[0] + ".txt"
            gt_box = load_gt_phone_box(label_path, w, h)

            result = phone_model.predict(image, verbose=False, conf=PHONE_SPECIALIST_CONFIDENCE_THRESHOLD,
                                          device=args.device)[0]
            pred_boxes = [
                tuple(float(v) for v in box.xyxy[0])
                for box in result.boxes if int(box.cls[0]) == PHONE_SPECIALIST_CLASS
            ]
            if gt_box is None:
                fp += 1 if pred_boxes else 0
                tn += 0 if pred_boxes else 1
            else:
                if pred_boxes and max(iou(gt_box, pb) for pb in pred_boxes) >= IOU_THRESH:
                    tp += 1
                else:
                    fn += 1

            face_detector.setInputSize((w, h))
            _, faces = face_detector.detect(image)
            if faces is not None and len(faces) > 0:
                face_hit += 1

        n = len(frames)
        precision = tp / (tp + fp) if (tp + fp) else float("nan")
        recall = tp / (tp + fn) if (tp + fn) else float("nan")
        face_rate = face_hit / n if n else float("nan")
        provenance = "train+holdout" if (any_train and any_holdout) else ("train-only" if any_train else "holdout-only")

        rows.append((g, n, precision, recall, face_rate, provenance))
        agg["tp"] += tp
        agg["fp"] += fp
        agg["fn"] += fn
        agg["tn"] += tn
        agg["face_hit"] += face_hit
        agg["n"] += n

    overall_precision = agg["tp"] / (agg["tp"] + agg["fp"]) if (agg["tp"] + agg["fp"]) else float("nan")
    overall_recall = agg["tp"] / (agg["tp"] + agg["fn"]) if (agg["tp"] + agg["fn"]) else float("nan")
    overall_face_rate = agg["face_hit"] / agg["n"] if agg["n"] else float("nan")

    print(f"model: {args.model}")
    print(f"{'group':<20} {'n':>5} {'phone_prec':>10} {'phone_recall':>12} {'face_rate':>10}  provenance")
    for g, n, p, r, fr, prov in rows:
        p_str = f"{p:.3f}" if p == p else "n/a"
        r_str = f"{r:.3f}" if r == r else "n/a"
        print(f"{g:<20} {n:>5} {p_str:>10} {r_str:>12} {fr:>10.3f}  {prov}")
    print(f"{'OVERALL':<20} {agg['n']:>5} {overall_precision:>10.3f} {overall_recall:>12.3f} {overall_face_rate:>10.3f}")

    print("\nGroups more than 15 points below overall on phone recall or face rate (possible disparity, needs "
          "follow-up, not a conclusion on its own):")
    flagged = False
    for g, n, p, r, fr, prov in rows:
        if r == r and overall_recall == overall_recall and (overall_recall - r) > 0.15:
            print(f"  {g}: phone recall {r:.3f} vs overall {overall_recall:.3f} ({prov})")
            flagged = True
        if fr == fr and overall_face_rate == overall_face_rate and (overall_face_rate - fr) > 0.15:
            print(f"  {g}: face detection rate {fr:.3f} vs overall {overall_face_rate:.3f} ({prov})")
            flagged = True
    if not flagged:
        print("  none")


if __name__ == "__main__":
    main()
