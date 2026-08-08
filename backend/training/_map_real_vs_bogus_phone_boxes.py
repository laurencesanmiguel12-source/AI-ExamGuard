"""Classifies each draft-labeled frame in personal_phone_video_review/ as likely a real phone
detection vs. the face-shaped false positive found 2026-08-08 (phone_specialist.pt scoring ~0.9
confidence on a plain face, near-identical box to the simultaneously-detected face box).

First attempt (single-phone-box IoU-vs-face-box) was too noisy to trust - the false-positive box's
exact position jitters slightly frame to frame, dipping in and out of the IoU cutoff without any
real phone appearing, producing ~200 tiny fragmented ranges spanning the whole video. This version
uses a more robust signal instead: the persistent false positive is present in nearly every frame,
so a SECOND, independent phone box in the same frame is what actually signals something extra (a
real phone) was also detected - a count-based check tolerates the bogus box's jitter instead of
being confused by it.

Usage: python _map_real_vs_bogus_phone_boxes.py
"""
import glob
import os

REVIEW_DIR = os.path.join(os.path.dirname(__file__), "datasets", "oep-msu", "personal_phone_video_review")
FACE_CLASS = 1
PHONE_CLASS = 0
IOU_DEDUPE_THRESHOLD = 0.5  # merge near-duplicate phone boxes before counting


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
    area_a = aw * ah
    area_b = bw * bh
    return inter / (area_a + area_b - inter)


def distinct_phone_box_count(phone_boxes):
    kept = []
    for box in phone_boxes:
        if all(iou(box, k) < IOU_DEDUPE_THRESHOLD for k in kept):
            kept.append(box)
    return len(kept)


def classify(label_path):
    phone_boxes = []
    with open(label_path) as f:
        for line in f:
            parts = line.split()
            if not parts:
                continue
            if int(parts[0]) == PHONE_CLASS:
                phone_boxes.append(tuple(float(x) for x in parts[1:5]))

    if not phone_boxes:
        return "no_phone_box"
    return "real_candidate" if distinct_phone_box_count(phone_boxes) >= 2 else "bogus_only"


def frame_index(path):
    return int(os.path.basename(path).split("_")[-1].split(".")[0])


def summarize_ranges(indices):
    if not indices:
        return []
    indices = sorted(indices)
    ranges = [[indices[0], indices[0]]]
    for i in indices[1:]:
        if i <= ranges[-1][1] + 1:
            ranges[-1][1] = i
        else:
            ranges.append([i, i])
    return ranges


def main():
    label_paths = sorted(glob.glob(os.path.join(REVIEW_DIR, "*.txt")))
    label_paths = [p for p in label_paths if os.path.basename(p) != "classes.txt"]

    by_category = {"no_phone_box": [], "bogus_only": [], "real_candidate": []}
    for path in label_paths:
        idx = frame_index(path)
        by_category[classify(path)].append(idx)

    print(f"{len(label_paths)} labeled frames total\n")
    fps = 15.16
    for category, indices in by_category.items():
        ranges = summarize_ranges(indices)
        print(f"{category}: {len(indices)} frames, {len(ranges)} contiguous range(s)")
        for lo, hi in ranges:
            print(f"    frames {lo:04d}-{hi:04d}  (~{lo/fps:.1f}s-{hi/fps:.1f}s)  [{hi-lo+1} frames]")
        print()


if __name__ == "__main__":
    main()
