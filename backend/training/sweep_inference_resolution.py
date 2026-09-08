"""Does raising the whole-frame inference resolution help phone detection, and what does it cost?

Production infers at 416: phone_specialist.pt carries imgsz=416 from training in its own overrides,
and neither object_detection_service.py nor eval_common.py passes an override, so that is what the
deployed pipeline actually uses (verified 2026-09-08, not assumed). Raising it is a one-argument
change, which makes it worth measuring rather than arguing about.

Run this against the CORRECTED frozen holdout (see fix_frozen_holdout_device_labels.py). Note the
headroom is small by construction - after the label fix, production misses exactly 1 of 76
phone-positive frames - so the question this answers is mostly "does higher resolution cost
precision and latency for nothing", not "how much recall does it buy".

Reports the presence metric (production's real behaviour) plus mean whole-frame latency per
resolution, so the accuracy change can be read against the capacity cost. The load test put the
ceiling near 5 concurrent students at 1 fps with YOLO inference as the binding constraint, so a
2x latency increase is a real capacity decision, not a free knob.

Usage: ../.venv/Scripts/python.exe sweep_inference_resolution.py [--sizes 416 640 960]
"""
import argparse
import os
import time

import cv2
from ultralytics import YOLO

from eval_common import analyze_frame, load_gt_phone_boxes

HOLDOUT = os.path.join(os.path.dirname(__file__), "datasets", "oep-msu", "frozen_holdout")
POSE_MODEL_PATH = os.path.join(os.path.dirname(__file__), "..", "app", "resources", "yolov8n-pose.pt")
THRESHOLD = 0.35
IOU_THRESH = 0.3


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=os.path.join(
        os.path.dirname(__file__), "..", "app", "resources", "phone_specialist.pt"))
    ap.add_argument("--sizes", nargs="+", type=int, default=[416, 640, 960])
    ap.add_argument("--device", default="cpu")
    args = ap.parse_args()

    phone_model = YOLO(args.model)
    pose_model = YOLO(POSE_MODEL_PATH)
    files = sorted(f for f in os.listdir(HOLDOUT) if f.lower().endswith(".jpg"))
    cache = []
    for f in files:
        img = cv2.imread(os.path.join(HOLDOUT, f))
        h, w = img.shape[:2]
        cache.append((img, load_gt_phone_boxes(os.path.join(HOLDOUT, os.path.splitext(f)[0] + ".txt"), w, h)))
    n_pos = sum(1 for _, g in cache if g)
    print(f"corrected frozen holdout: {len(files)} frames, {n_pos} phone-positive, "
          f"{len(files) - n_pos} negative   (threshold {THRESHOLD})\n")
    print(f"{'imgsz':>6} {'prec':>7} {'recall':>7} {'F1':>7} {'TP':>4} {'FP':>4} {'FN':>4} {'ms/frame':>9} {'cost':>6}")

    base_ms = None
    for size in args.sizes:
        tp = fp = fn = 0
        t0 = time.perf_counter()
        for img, gt in cache:
            r = analyze_frame(img, gt, phone_model, pose_model, THRESHOLD, IOU_THRESH,
                              args.device, imgsz=size)
            hit = (r["max_conf_any"] >= THRESHOLD) or r["fallback_hit"]
            if gt:
                tp += hit
                fn += not hit
            else:
                fp += hit
        ms = (time.perf_counter() - t0) / len(cache) * 1000
        base_ms = base_ms or ms
        prec = tp / (tp + fp) if (tp + fp) else float("nan")
        rec = tp / (tp + fn) if (tp + fn) else float("nan")
        f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else float("nan")
        print(f"{size:>6} {prec:>7.3f} {rec:>7.3f} {f1:>7.3f} {tp:>4} {fp:>4} {fn:>4} "
              f"{ms:>9.0f} {ms / base_ms:>5.1f}x")

    print("\nNote: ms/frame here is the FULL pipeline (whole-frame pass + pose model + any "
          "hand-crop fallback), so it is higher than a bare whole-frame predict() and is the "
          "number that actually bounds concurrent students.")


if __name__ == "__main__":
    main()
