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

**What this measures**: now shares eval_common.py's analyze_frame with evaluate_frozen_holdout.py -
this used to run its own simpler whole-frame-only prediction with no pose-guided hand-crop fallback
and no presence/localized distinction, which produced a real false alarm: subject06 was flagged with
phone recall 0.741 vs 0.918 overall (2026-08-01), and investigating found the deployed model's actual
student-facing behavior (presence, matching object_detection_service.py's real check) was fine
(0.898) - the old localized-only number was comparing predictions against the WRONG ground-truth box
on subject06/01/24's multi-box frames (see load_gt_phone_boxes' docstring: these subjects have
residual bogus eye-tracker-device boxes deliberately left alongside real phone boxes rather than
surgically split out, and the old single-box gt loader just grabbed whichever line came first).
Both numbers are now reported per group - **presence is the real comparison** (what students
actually experience), localized is a model-quality diagnostic, matching evaluate_frozen_holdout.py's
already-established convention.

- Phone detection: the fine-tuned specialist (phone_specialist.pt by default - the currently
  DEPLOYED model, since this audits what students actually experience, not a training candidate) at
  the app's real production confidence threshold, against the human-reviewed ground-truth boxes
  already in every group's .txt labels, INCLUDING the pose-guided hand-crop fallback (previously
  missing entirely from this script).
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

from eval_common import analyze_frame, load_gt_phone_boxes

BATCH_DIR = os.path.join(os.path.dirname(__file__), "datasets", "oep-msu", "annotation_batch")
HOLDOUT_DIR = os.path.join(os.path.dirname(__file__), "datasets", "oep-msu", "frozen_holdout")
YUNET_PATH = os.path.join(os.path.dirname(__file__), "..", "app", "resources", "face_detection_yunet_2023mar.onnx")
POSE_MODEL_PATH = os.path.join(os.path.dirname(__file__), "..", "app", "resources", "yolov8n-pose.pt")

# Copied from app/services/object_detection_service.py, same convention/reasoning as
# evaluate_frozen_holdout.py - keep in sync by hand.
PHONE_SPECIALIST_CONFIDENCE_THRESHOLD = 0.35
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
    pose_model = YOLO(POSE_MODEL_PATH)
    face_detector = cv2.FaceDetectorYN_create(YUNET_PATH, "", (320, 320), 0.6, 0.3, 5000)

    groups = collect_frames()

    rows = []
    agg = {"tp_p": 0, "fp_p": 0, "fn_p": 0, "tp_l": 0, "fn_l": 0, "face_hit": 0, "n": 0}

    for g in sorted(groups):
        frames = groups[g]
        tp_p = fp_p = fn_p = tp_l = fn_l = 0  # _p = presence, _l = localized
        face_hit = 0
        any_train = any(in_train for _, in_train in frames)
        any_holdout = any(not in_train for _, in_train in frames)

        for img_path, _ in frames:
            image = cv2.imread(img_path)
            h, w = image.shape[:2]
            label_path = os.path.splitext(img_path)[0] + ".txt"
            gt_boxes = load_gt_phone_boxes(label_path, w, h)
            has_gt = bool(gt_boxes)

            r = analyze_frame(image, gt_boxes, phone_model, pose_model,
                               PHONE_SPECIALIST_CONFIDENCE_THRESHOLD, IOU_THRESH, args.device)
            presence_hit = (r["max_conf_any"] >= PHONE_SPECIALIST_CONFIDENCE_THRESHOLD) or r["fallback_hit"]
            localized_hit = (
                (r["best_match_conf"] is not None and r["best_match_conf"] >= PHONE_SPECIALIST_CONFIDENCE_THRESHOLD)
                or (r["fallback_hit"] and r["fallback_matched_gt"])
            )

            if has_gt:
                tp_p += int(presence_hit)
                fn_p += int(not presence_hit)
                tp_l += int(bool(localized_hit))
                fn_l += int(not localized_hit)
            else:
                fp_p += int(presence_hit)

            face_detector.setInputSize((w, h))
            _, faces = face_detector.detect(image)
            if faces is not None and len(faces) > 0:
                face_hit += 1

        n = len(frames)
        precision_p = tp_p / (tp_p + fp_p) if (tp_p + fp_p) else float("nan")
        recall_p = tp_p / (tp_p + fn_p) if (tp_p + fn_p) else float("nan")
        recall_l = tp_l / (tp_l + fn_l) if (tp_l + fn_l) else float("nan")
        face_rate = face_hit / n if n else float("nan")
        provenance = "train+holdout" if (any_train and any_holdout) else ("train-only" if any_train else "holdout-only")

        rows.append((g, n, precision_p, recall_p, recall_l, face_rate, provenance))
        agg["tp_p"] += tp_p
        agg["fp_p"] += fp_p
        agg["fn_p"] += fn_p
        agg["tp_l"] += tp_l
        agg["fn_l"] += fn_l
        agg["face_hit"] += face_hit
        agg["n"] += n

    overall_precision_p = agg["tp_p"] / (agg["tp_p"] + agg["fp_p"]) if (agg["tp_p"] + agg["fp_p"]) else float("nan")
    overall_recall_p = agg["tp_p"] / (agg["tp_p"] + agg["fn_p"]) if (agg["tp_p"] + agg["fn_p"]) else float("nan")
    overall_recall_l = agg["tp_l"] / (agg["tp_l"] + agg["fn_l"]) if (agg["tp_l"] + agg["fn_l"]) else float("nan")
    overall_face_rate = agg["face_hit"] / agg["n"] if agg["n"] else float("nan")

    print(f"model: {args.model}")
    print(f"{'group':<20} {'n':>5} {'prec(pres)':>10} {'recall(pres)':>12} {'recall(loc)':>11} {'face_rate':>10}  provenance")
    for g, n, p, r_p, r_l, fr, prov in rows:
        p_str = f"{p:.3f}" if p == p else "n/a"
        rp_str = f"{r_p:.3f}" if r_p == r_p else "n/a"
        rl_str = f"{r_l:.3f}" if r_l == r_l else "n/a"
        print(f"{g:<20} {n:>5} {p_str:>10} {rp_str:>12} {rl_str:>11} {fr:>10.3f}  {prov}")
    print(f"{'OVERALL':<20} {agg['n']:>5} {overall_precision_p:>10.3f} {overall_recall_p:>12.3f} "
          f"{overall_recall_l:>11.3f} {overall_face_rate:>10.3f}")

    print("\nGroups more than 15 points below overall on PRESENCE phone recall (what students actually "
          "experience) or face rate (possible disparity, needs follow-up, not a conclusion on its own):")
    flagged = False
    for g, n, p, r_p, r_l, fr, prov in rows:
        if r_p == r_p and overall_recall_p == overall_recall_p and (overall_recall_p - r_p) > 0.15:
            print(f"  {g}: presence phone recall {r_p:.3f} vs overall {overall_recall_p:.3f} ({prov})")
            flagged = True
        if fr == fr and overall_face_rate == overall_face_rate and (overall_face_rate - fr) > 0.15:
            print(f"  {g}: face detection rate {fr:.3f} vs overall {overall_face_rate:.3f} ({prov})")
            flagged = True
    if not flagged:
        print("  none")

    print("\nGroups where LOCALIZED recall trails PRESENCE recall by a lot (model finds a phone but boxes "
          "it away from the labeled one - often a residual multi-box ground-truth artifact, not a real "
          "detection gap; see load_gt_phone_boxes' docstring before treating this as a model problem):")
    loc_flagged = False
    for g, n, p, r_p, r_l, fr, prov in rows:
        if r_p == r_p and r_l == r_l and (r_p - r_l) > 0.10:
            print(f"  {g}: presence {r_p:.3f} vs localized {r_l:.3f}")
            loc_flagged = True
    if not loc_flagged:
        print("  none")


if __name__ == "__main__":
    main()
