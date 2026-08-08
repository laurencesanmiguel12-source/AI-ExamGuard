"""Applies the AI-assisted correction pass to personal_phone_video_review/ draft labels, replacing
a manual LabelImg session at the user's explicit request ("go label it for me", 2026-08-08).

Built from direct inspection of the raw .txt files plus targeted visual spot-checks (not just the
box-count/IoU-fragmentation heuristics tried earlier, which were abandoned as unreliable - see
_map_real_vs_bogus_phone_boxes.py). Two independent, always-on spurious detections were found:

1. A face-shaped false positive: phone_specialist.pt fires a phone box nearly identical to the
   YuNet face box on almost every single frame, regardless of whether a phone is visible.
   IoU(phone_box, face_box) is cleanly bimodal across all 3043 phone boxes in this dataset - either
   ~0.0-0.2 (a real, spatially distinct detection) or ~0.8-1.0 (this false positive), with almost
   nothing in between (22 boxes out of 3043 fall in 0.3-0.6). Threshold 0.45 sits in that gap.
   Confirmed by direct visual inspection of multiple frames on both sides.

2. A second, independent false positive fixed at the bottom-left screen corner (cx<0.25, cy>0.85) -
   NOT explained by the face-anchor rule since it's spatially distinct from the face. Turned out to
   be a MIX: the user does genuinely rest/prop a real phone in roughly that same corner for some
   stretches of the video, so position alone can't separate real from bogus here (confirmed by
   directly viewing frame 0008 vs frame 1000 - nearly identical box coordinates, one is empty
   couch, the other is a real phone in a stand). Resolved with a pixel-level check instead: mean
   HSV saturation of the box crop is cleanly separated (empty couch/background: ~30-63, real phone
   in view: ~68-186, confirmed against 20+ hand-checked frames spanning both clusters and the
   boundary). Threshold 65.

Every other phone box (not face-anchored, not in that corner) was checked for spatial spread - the
~720 remaining "other" boxes cluster around chest/mouth height (cy 0.8-0.9) across a WIDE range of
x-positions, consistent with genuine varied hand-holding, not a second fixed-position artifact -
these are trusted as real and left untouched.

**This is an AI visual-review substitute for manual LabelImg, not a literal human pass.** Per this
project's own established discipline (see ai_examguard project memory on why "all validated"
claims on manual labeling get spot-checked, and why offline-derived rules get live-tested before
being trusted) - run with no args first for a dry-run report, inspect a fresh sample of corrected
frames before trusting this for a retrain, and treat this file's docstring as the audit trail if
something looks wrong later.

Usage: python apply_phone_label_corrections.py [--apply]
"""
import glob
import os
import sys

import cv2

REVIEW_DIR = os.path.join(os.path.dirname(__file__), "datasets", "oep-msu", "personal_phone_video_review")
PHONE_CLASS, FACE_CLASS = 0, 1
FACE_IOU_THRESHOLD = 0.45
CORNER_SAT_THRESHOLD = 65.0
CORNER_MARGIN = 0.3


def iou(a, b):
    acx, acy, aw, ah = a
    bcx, bcy, bw, bh = b
    ax1, ay1, ax2, ay2 = acx - aw / 2, acy - ah / 2, acx + aw / 2, acy + ah / 2
    bx1, by1, bx2, by2 = bcx - bw / 2, bcy - bh / 2, bcx + bw / 2, bcy + bh / 2
    ix1, iy1 = max(ax1, bx1), max(ay1, by1)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    if ix2 <= ix1 or iy2 <= iy1:
        return 0.0
    inter = (ix2 - ix1) * (iy2 - iy1)
    return inter / (aw * ah + bw * bh - inter)


def is_corner(box):
    return box[0] < 0.25 and box[1] > 0.85


def corner_has_phone(image, box):
    h, w = image.shape[:2]
    cx, cy, bw, bh = box
    bw2, bh2 = bw * (1 + CORNER_MARGIN), bh * (1 + CORNER_MARGIN)
    x1, y1 = max(0, int((cx - bw2 / 2) * w)), max(0, int((cy - bh2 / 2) * h))
    x2, y2 = min(w, int((cx + bw2 / 2) * w)), min(h, int((cy + bh2 / 2) * h))
    crop = image[y1:y2, x1:x2]
    if crop.size == 0:
        return False
    hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
    return hsv[:, :, 1].mean() >= CORNER_SAT_THRESHOLD


def main():
    apply = "--apply" in sys.argv
    label_paths = sorted(
        p for p in glob.glob(os.path.join(REVIEW_DIR, "*.txt")) if os.path.basename(p) != "classes.txt"
    )

    dropped_face_anchor = 0
    dropped_corner_empty = 0
    kept_corner_phone = 0
    kept_other = 0

    for path in label_paths:
        phone_boxes, face_box = [], None
        for line in open(path):
            parts = line.split()
            if not parts:
                continue
            cls_id = int(parts[0])
            box = tuple(float(x) for x in parts[1:5])
            if cls_id == PHONE_CLASS:
                phone_boxes.append(box)
            elif cls_id == FACE_CLASS:
                face_box = box

        if face_box is None or not phone_boxes:
            continue

        image = None
        kept_boxes = []
        for box in phone_boxes:
            if iou(box, face_box) >= FACE_IOU_THRESHOLD:
                dropped_face_anchor += 1
                continue
            if is_corner(box):
                if image is None:
                    image = cv2.imread(path.replace(".txt", ".jpg"))
                if corner_has_phone(image, box):
                    kept_corner_phone += 1
                    kept_boxes.append(box)
                else:
                    dropped_corner_empty += 1
                continue
            kept_other += 1
            kept_boxes.append(box)

        if apply:
            with open(path, "w") as f:
                for box in kept_boxes:
                    f.write(f"{PHONE_CLASS} {box[0]:.6f} {box[1]:.6f} {box[2]:.6f} {box[3]:.6f}\n")
                f.write(f"{FACE_CLASS} {face_box[0]:.6f} {face_box[1]:.6f} {face_box[2]:.6f} {face_box[3]:.6f}\n")

    print(f"{'APPLIED' if apply else 'DRY RUN'}")
    print(f"  dropped (face-shaped FP, IoU>={FACE_IOU_THRESHOLD}): {dropped_face_anchor}")
    print(f"  dropped (corner FP, empty background):              {dropped_corner_empty}")
    print(f"  kept (corner, real phone in stand):                 {kept_corner_phone}")
    print(f"  kept (other, real handheld detections):             {kept_other}")


if __name__ == "__main__":
    main()
