"""Shared evaluation core for evaluate_frozen_holdout.py and threshold_sweep.py.

Exists to fix two real problems found on 2026-07-30 while sweeping confidence thresholds:

1. **Presence vs. localization mismatch.** object_detection_service.py's actual deployed check is
   `phone_detected = PHONE_SPECIALIST_CLASS in phone_classes` - a pure presence check with no
   location awareness at all. The first version of evaluate_frozen_holdout.py required an IoU match
   against the ground-truth box to count a detection as correct, which is a different (stricter)
   question than what production actually asks, and silently undercounted false positives (a
   wrong-location detection on a positive frame was only ever counted as a missed true positive,
   never as the false positive it also is). This module computes both: `max_conf_any` (drives the
   presence-based metric, matching production exactly) and `best_match_conf` (drives an IoU-gated
   localized metric, useful as a model-quality diagnostic - e.g. it's what would have caught "right
   answer for the wrong reason" cases like the eye-tracker-device confounder before those labels
   were fixed).

2. **Missing the pose-guided hand-crop fallback.** Production doesn't stop at the whole-frame pass -
   if that misses, it re-checks small crops around detected wrist keypoints
   (WRIST_VISIBILITY_THRESHOLD / HAND_CROP_SIZE / HAND_REGION_PHONE_THRESHOLD, copied below from
   object_detection_service.py). Neither eval script modeled this before, so both were measuring a
   strictly weaker pipeline than what's actually deployed - real recall was being understated.

The fallback's own thresholds are NOT swept by threshold_sweep.py - only
PHONE_SPECIALIST_CONFIDENCE_THRESHOLD (the whole-frame pass) is being tuned right now. The fallback
runs at its existing fixed calibration in every analysis, exactly matching how it would actually
behave in production regardless of what the whole-frame threshold is set to. Tuning the fallback's
own thresholds is a distinct, not-yet-done follow-up (they're flagged in the source as "not yet
tuned against real hardware" independently of the whole-frame threshold).
"""
import os

PHONE_SPECIALIST_CLASS = 0
LEFT_WRIST_KPT = 9
RIGHT_WRIST_KPT = 10
WRIST_VISIBILITY_THRESHOLD = 0.10
HAND_CROP_SIZE = 120
HAND_REGION_PHONE_THRESHOLD = 0.20


def load_gt_phone_box(label_path, w, h):
    if not os.path.exists(label_path):
        return None
    with open(label_path) as f:
        for line in f:
            parts = line.split()
            if int(parts[0]) != PHONE_SPECIALIST_CLASS:
                continue
            cx, cy, bw, bh = (float(v) for v in parts[1:5])
            return ((cx - bw / 2) * w, (cy - bh / 2) * h, (cx + bw / 2) * w, (cy + bh / 2) * h)
    return None


def iou(a, b):
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    ix1, iy1 = max(ax1, bx1), max(ay1, by1)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    inter = max(0.0, ix2 - ix1) * max(0.0, iy2 - iy1)
    union = (ax2 - ax1) * (ay2 - ay1) + (bx2 - bx1) * (by2 - by1) - inter
    return inter / union if union > 0 else 0.0


def _wrist_points(pose_result, image_shape):
    height, width = image_shape[:2]
    points = []
    if pose_result.keypoints is None:
        return points
    for person_kpts in pose_result.keypoints.data:
        for idx in (LEFT_WRIST_KPT, RIGHT_WRIST_KPT):
            x, y, conf = person_kpts[idx].tolist()
            if conf >= WRIST_VISIBILITY_THRESHOLD:
                points.append((min(max(int(x), 0), width), min(max(int(y), 0), height)))
    return points


def _hand_crop(image, x, y):
    height, width = image.shape[:2]
    half = HAND_CROP_SIZE // 2
    x1, y1 = max(x - half, 0), max(y - half, 0)
    x2, y2 = min(x + half, width), min(y + half, height)
    if x2 <= x1 or y2 <= y1:
        return None, None
    return image[y1:y2, x1:x2], (x1, y1)


def analyze_frame(image, gt_box, phone_model, pose_model, conf_floor, iou_thresh, device="cpu"):
    """Returns dict: max_conf_any, best_match_conf (or None), fallback_hit (bool),
    fallback_matched_gt (bool or None - only meaningful if fallback_hit and gt_box is not None)."""
    h, w = image.shape[:2]

    result = phone_model.predict(image, verbose=False, conf=conf_floor, device=device)[0]
    preds = [
        (float(box.conf[0]), tuple(float(v) for v in box.xyxy[0]))
        for box in result.boxes if int(box.cls[0]) == PHONE_SPECIALIST_CLASS
    ]
    max_conf_any = max((c for c, _ in preds), default=0.0)
    best_match_conf = None
    if gt_box is not None and preds:
        matching = [c for c, box in preds if iou(gt_box, box) >= iou_thresh]
        if matching:
            best_match_conf = max(matching)

    # Pose-guided hand-crop fallback, matching object_detection_service.py's _phone_near_hands
    # exactly - fixed thresholds, not part of the sweep.
    pose_result = pose_model.predict(image, verbose=False, device=device)[0]
    fallback_hit = False
    fallback_matched_gt = None
    for x, y in _wrist_points(pose_result, image.shape):
        crop, origin = _hand_crop(image, x, y)
        if crop is None or crop.size == 0:
            continue
        crop_result = phone_model.predict(crop, verbose=False, conf=HAND_REGION_PHONE_THRESHOLD, device=device)[0]
        crop_boxes = [
            tuple(float(v) for v in box.xyxy[0])
            for box in crop_result.boxes if int(box.cls[0]) == PHONE_SPECIALIST_CLASS
        ]
        if crop_boxes:
            fallback_hit = True
            if gt_box is not None:
                ox, oy = origin
                for cb in crop_boxes:
                    full_box = (cb[0] + ox, cb[1] + oy, cb[2] + ox, cb[3] + oy)
                    if iou(gt_box, full_box) >= iou_thresh:
                        fallback_matched_gt = True
                if fallback_matched_gt is None:
                    fallback_matched_gt = False
            break

    return {
        "max_conf_any": max_conf_any,
        "best_match_conf": best_match_conf,
        "fallback_hit": fallback_hit,
        "fallback_matched_gt": fallback_matched_gt,
    }
