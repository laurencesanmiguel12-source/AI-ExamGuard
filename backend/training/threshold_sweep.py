"""One-time confidence-threshold analysis against the frozen holdout (see
ai_examguard_frozen_holdout_eval memory) - answers "is 0.35 actually the best operating point,"
which the threshold's own comment in object_detection_service.py admits was never checked
("not yet tuned against real hardware... same starting-point-then-adjust approach").

Runs the FULL production pipeline exactly once per holdout image (whole-frame phone_specialist pass
at a low confidence floor to capture every candidate score, plus the pose-guided hand-crop fallback
at its real fixed thresholds - see eval_common.py's docstring for why both of these matter and what
was wrong with the first version of this analysis). The whole-frame pass's threshold is then swept
across many values purely analytically from that single pass's recorded scores - re-running
inference per candidate threshold would mean looking at the holdout many times instead of once.

Reports two metrics side by side:
- "presence" - matches object_detection_service.py's real behavior exactly (any phone-class
  detection anywhere in frame, whole-frame OR fallback, counts). This is the number that should
  drive an actual threshold decision.
- "localized" - additionally requires the detection to overlap the real ground-truth phone box
  (IoU-gated). Diagnostic only: flags "right answer for the wrong reason" cases (e.g. the
  eye-tracker-device confounder fixed earlier this session) that the presence metric can't see.

Usage: ../.venv/Scripts/python.exe threshold_sweep.py [--model ../app/resources/phone_specialist.pt]
"""
import argparse
import os

import cv2
from ultralytics import YOLO

from eval_common import analyze_frame, load_gt_phone_boxes

HOLDOUT_DIR = os.path.join(os.path.dirname(__file__), "datasets", "oep-msu", "frozen_holdout")
POSE_MODEL_PATH = os.path.join(os.path.dirname(__file__), "..", "app", "resources", "yolov8n-pose.pt")
CONF_FLOOR = 0.05
IOU_THRESH = 0.3
CURRENT_PRODUCTION_THRESHOLD = 0.35


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default=os.path.join(
        os.path.dirname(__file__), "..", "app", "resources", "phone_specialist.pt"))
    parser.add_argument("--device", default="cpu")
    args = parser.parse_args()

    if not os.path.isdir(HOLDOUT_DIR) or not os.listdir(HOLDOUT_DIR):
        print(f"{HOLDOUT_DIR} is empty - run make_frozen_holdout.py first.")
        return

    phone_model = YOLO(args.model)
    pose_model = YOLO(POSE_MODEL_PATH)
    image_files = sorted(f for f in os.listdir(HOLDOUT_DIR) if f.lower().endswith(".jpg"))

    frames = []  # (has_gt, max_conf_any, best_match_conf, fallback_hit, fallback_matched_gt)
    total_gt = 0

    for fname in image_files:
        img_path = os.path.join(HOLDOUT_DIR, fname)
        label_path = os.path.join(HOLDOUT_DIR, os.path.splitext(fname)[0] + ".txt")
        image = cv2.imread(img_path)
        h, w = image.shape[:2]
        gt_boxes = load_gt_phone_boxes(label_path, w, h)
        if gt_boxes:
            total_gt += 1

        result = analyze_frame(image, gt_boxes, phone_model, pose_model, CONF_FLOOR, IOU_THRESH, args.device)
        frames.append((bool(gt_boxes), result["max_conf_any"], result["best_match_conf"],
                       result["fallback_hit"], result["fallback_matched_gt"]))

    thresholds = sorted(set([round(t * 0.05, 2) for t in range(1, 20)] + [CURRENT_PRODUCTION_THRESHOLD]))

    print(f"model: {args.model}")
    print(f"frozen holdout: {len(image_files)} frames, {total_gt} phone-positive, "
          f"{len(image_files) - total_gt} negative")
    header = f"{'thresh':>7} | {'prec(pres)':>10} {'rec(pres)':>9} {'f1(pres)':>8} {'tp':>4} {'fp':>4} | " \
             f"{'prec(loc)':>9} {'rec(loc)':>8} {'f1(loc)':>7}"
    print(header)

    best = {"presence": (-1, None), "localized": (-1, None)}
    for t in thresholds:
        # presence-based (matches real production behavior)
        tp_p = fp_p = 0
        for has_gt, max_conf, _, fb_hit, _ in frames:
            detected = (max_conf >= t) or fb_hit
            if has_gt:
                tp_p += int(detected)
            else:
                fp_p += int(detected)
        fn_p = total_gt - tp_p
        prec_p = tp_p / (tp_p + fp_p) if (tp_p + fp_p) else float("nan")
        rec_p = tp_p / total_gt if total_gt else float("nan")
        f1_p = 2 * prec_p * rec_p / (prec_p + rec_p) if prec_p == prec_p and (prec_p + rec_p) else float("nan")

        # localized/diagnostic (IoU-gated)
        tp_l = fp_l = 0
        for has_gt, max_conf, match_conf, fb_hit, fb_matched in frames:
            if has_gt:
                localized_hit = (match_conf is not None and match_conf >= t) or (fb_hit and fb_matched)
                tp_l += int(bool(localized_hit))
            else:
                fp_l += int((max_conf >= t) or fb_hit)
        fn_l = total_gt - tp_l
        prec_l = tp_l / (tp_l + fp_l) if (tp_l + fp_l) else float("nan")
        rec_l = tp_l / total_gt if total_gt else float("nan")
        f1_l = 2 * prec_l * rec_l / (prec_l + rec_l) if prec_l == prec_l and (prec_l + rec_l) else float("nan")

        marker = "  <- current production" if abs(t - CURRENT_PRODUCTION_THRESHOLD) < 1e-9 else ""
        print(f"{t:>7.2f} | {prec_p:>10.3f} {rec_p:>9.3f} {f1_p:>8.3f} {tp_p:>4} {fp_p:>4} | "
              f"{prec_l:>9.3f} {rec_l:>8.3f} {f1_l:>7.3f}{marker}")

        if f1_p == f1_p and f1_p > best["presence"][0]:
            best["presence"] = (f1_p, t)
        if f1_l == f1_l and f1_l > best["localized"][0]:
            best["localized"] = (f1_l, t)

    print(f"\nbest presence-based F1 = {best['presence'][0]:.3f} at threshold {best['presence'][1]}")
    print(f"best localized F1 = {best['localized'][0]:.3f} at threshold {best['localized'][1]}")


if __name__ == "__main__":
    main()
