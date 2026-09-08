"""Two diagnostics that should precede any further phone-detector retraining.

Motivated by a 3-for-3 run of retrains that all "regressed" the frozen holdout (F1 0.833, 0.838,
0.829 vs production 0.854) - before chasing a data or architecture fix, establish (a) whether
those differences are distinguishable from noise at all on a 96-positive holdout, and (b) whether
the misses are weak-but-present detections or genuine blindness, because those need opposite fixes.

Diagnostic 1 - PAIRED BOOTSTRAP. Resamples the holdout frames with replacement and recomputes
every model's F1 on the same resample, so the per-model CI and the paired difference CI come from
identical frame draws. A difference CI that straddles zero means the holdout cannot tell the two
models apart, and any "regression" read off a single point estimate is unfounded.

Diagnostic 2 - FALSE-NEGATIVE CONFIDENCE PROFILE. Runs the pipeline at a low confidence floor
(0.05) so a sub-threshold detection is still recorded, then buckets the frames the model misses at
the production threshold. Misses carrying 0.15-0.34 mean the model sees the phone and the
threshold/corroboration logic discards it (fix: tuning). Misses at ~0.0 mean it sees nothing
(fix: resolution, or data targeted at that condition). Reported separately for the whole-frame
pass and after the pose-guided hand-crop fallback, since the fallback is production's real second
chance.

Runs the FULL production pipeline via eval_common.analyze_frame, same as evaluate_frozen_holdout.py.

Usage:
  ../.venv/Scripts/python.exe diagnose_frozen_holdout.py \
      --models ../app/resources/phone_specialist.pt runs/phone_face_specialist-13/weights/best.pt
"""
import argparse
import csv
import os
import random

import cv2
from ultralytics import YOLO

from eval_common import analyze_frame, load_gt_phone_boxes

HOLDOUT_DIR = os.path.join(os.path.dirname(__file__), "datasets", "oep-msu", "frozen_holdout")
POSE_MODEL_PATH = os.path.join(os.path.dirname(__file__), "..", "app", "resources", "yolov8n-pose.pt")
OUT_CSV = os.path.join(os.path.dirname(__file__), "frozen_holdout_perframe.csv")

PRODUCTION_THRESHOLD = 0.35   # keep in sync with object_detection_service.py
CONF_FLOOR = 0.05             # low, so sub-threshold detections are still recorded
IOU_THRESH = 0.3
BOOTSTRAP_N = 10000
SEED = 20260908


def f1_from(rows, threshold):
    """presence-metric TP/FP/FN at `threshold`, matching production's location-free check."""
    tp = fp = fn = 0
    for has_gt, max_conf, fb_hit in rows:
        detected = (max_conf >= threshold) or fb_hit
        if has_gt:
            tp += detected
            fn += not detected
        else:
            fp += detected
    prec = tp / (tp + fp) if (tp + fp) else float("nan")
    rec = tp / (tp + fn) if (tp + fn) else float("nan")
    f1 = 2 * prec * rec / (prec + rec) if (prec == prec and (prec + rec)) else float("nan")
    return prec, rec, f1, tp, fp, fn


def collect(model_path, files, pose_model, device):
    phone_model = YOLO(model_path)
    out = []
    for i, fname in enumerate(files):
        img_path = os.path.join(HOLDOUT_DIR, fname)
        label_path = os.path.join(HOLDOUT_DIR, os.path.splitext(fname)[0] + ".txt")
        image = cv2.imread(img_path)
        h, w = image.shape[:2]
        gt_boxes = load_gt_phone_boxes(label_path, w, h)
        r = analyze_frame(image, gt_boxes, phone_model, pose_model, CONF_FLOOR, IOU_THRESH, device)
        out.append({
            "model": os.path.basename(os.path.dirname(os.path.dirname(model_path))) or model_path,
            "file": fname,
            "has_gt": bool(gt_boxes),
            "max_conf_any": round(r["max_conf_any"], 4),
            "best_match_conf": "" if r["best_match_conf"] is None else round(r["best_match_conf"], 4),
            "fallback_hit": r["fallback_hit"],
        })
        if (i + 1) % 50 == 0:
            print(f"    {i + 1}/{len(files)}", flush=True)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", nargs="+", required=True)
    ap.add_argument("--device", default="cpu")
    args = ap.parse_args()

    files = sorted(f for f in os.listdir(HOLDOUT_DIR) if f.lower().endswith(".jpg"))
    pose_model = YOLO(POSE_MODEL_PATH)

    per_model = {}
    all_rows = []
    for mp in args.models:
        print(f"\nscoring {mp} over {len(files)} frames at conf floor {CONF_FLOOR}...", flush=True)
        rows = collect(mp, files, pose_model, args.device)
        per_model[mp] = rows
        all_rows.extend(rows)

    with open(OUT_CSV, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(all_rows[0].keys()))
        w.writeheader()
        w.writerows(all_rows)
    print(f"\nper-frame scores -> {OUT_CSV}")

    # ---------- point estimates ----------
    print(f"\n=== point estimates at production threshold {PRODUCTION_THRESHOLD} ===")
    compact = {}
    for mp, rows in per_model.items():
        c = [(r["has_gt"], r["max_conf_any"], r["fallback_hit"]) for r in rows]
        compact[mp] = c
        prec, rec, f1, tp, fp, fn = f1_from(c, PRODUCTION_THRESHOLD)
        print(f"  {mp}\n      P={prec:.3f} R={rec:.3f} F1={f1:.3f}  TP={tp} FP={fp} FN={fn}")

    # ---------- diagnostic 1: paired bootstrap ----------
    print(f"\n=== diagnostic 1: paired bootstrap, {BOOTSTRAP_N} resamples ===")
    rnd = random.Random(SEED)
    n = len(files)
    idx_draws = [[rnd.randrange(n) for _ in range(n)] for _ in range(BOOTSTRAP_N)]

    dists = {}
    for mp, c in compact.items():
        vals = []
        for draw in idx_draws:
            sample = [c[i] for i in draw]
            vals.append(f1_from(sample, PRODUCTION_THRESHOLD)[2])
        vals = sorted(v for v in vals if v == v)
        dists[mp] = vals
        lo, hi = vals[int(0.025 * len(vals))], vals[int(0.975 * len(vals))]
        print(f"  {os.path.basename(mp):<12} F1 95% CI = [{lo:.3f}, {hi:.3f}]  (width {hi - lo:.3f})")

    models = list(compact.keys())
    if len(models) >= 2:
        a, b = models[0], models[1]
        diffs = []
        for draw in idx_draws:
            sa = [compact[a][i] for i in draw]
            sb = [compact[b][i] for i in draw]
            fa, fb = f1_from(sa, PRODUCTION_THRESHOLD)[2], f1_from(sb, PRODUCTION_THRESHOLD)[2]
            if fa == fa and fb == fb:
                diffs.append(fa - fb)
        diffs.sort()
        lo, hi = diffs[int(0.025 * len(diffs))], diffs[int(0.975 * len(diffs))]
        frac_a = sum(d > 0 for d in diffs) / len(diffs)
        print(f"\n  paired difference (A - B), A={os.path.basename(a)}, B={os.path.basename(b)}:")
        print(f"      median {diffs[len(diffs) // 2]:+.3f}   95% CI [{lo:+.3f}, {hi:+.3f}]")
        print(f"      A better in {100 * frac_a:.1f}% of resamples")
        if lo < 0 < hi:
            print("      -> CI STRADDLES ZERO: this holdout cannot distinguish these two models.")
        else:
            print("      -> CI excludes zero: the difference is real at this sample size.")

    # ---------- diagnostic 2: FN confidence profile ----------
    print(f"\n=== diagnostic 2: what the misses look like (threshold {PRODUCTION_THRESHOLD}) ===")
    buckets = [(0.0, 0.001, "0.00  (nothing detected at all)"),
               (0.001, 0.15, "0.00-0.15 (trace)"),
               (0.15, 0.25, "0.15-0.25"),
               (0.25, PRODUCTION_THRESHOLD, "0.25-0.35 (just under threshold)")]
    for mp, rows in per_model.items():
        misses = [r for r in rows
                  if r["has_gt"] and not ((r["max_conf_any"] >= PRODUCTION_THRESHOLD) or r["fallback_hit"])]
        print(f"\n  {os.path.basename(mp)} - {len(misses)} false negatives:")
        for lo_b, hi_b, label in buckets:
            k = [r for r in misses if lo_b <= r["max_conf_any"] < hi_b]
            print(f"      {label:<34} {len(k):>3}")
        recoverable = [r for r in misses if r["max_conf_any"] >= 0.15]
        print(f"      -> {len(recoverable)}/{len(misses)} carry a detection >=0.15 "
              f"(reachable by threshold/corroboration tuning, no retrain)")
        blind = [r for r in misses if r["max_conf_any"] < 0.001]
        print(f"      -> {len(blind)}/{len(misses)} are total blindness "
              f"(needs resolution or condition-targeted data)")
        if misses:
            print("      miss files (conf):", ", ".join(
                f"{r['file'][:26]}({r['max_conf_any']:.2f})" for r in misses[:12]))


if __name__ == "__main__":
    main()
