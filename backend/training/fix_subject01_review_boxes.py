"""Fix two specific defects found by spot-checking (rendering boxes and visually inspecting) the
subject01_phonewin_review/ batch after the human review pass, before it gets merged into
annotation_batch/:

1. A stationary background object (a wall-mounted device on a locker shelf, not a phone) is
   mislabeled "phone" in 195/232 frames, always at cx < 0.55 - confirmed via a real gap (no phone
   box anywhere in [0.5211, 0.5850]) that cleanly separates it from every genuine near-ear phone
   box. Dropped outright.
2. Many frames have 2+ overlapping/nested "phone" boxes for the same physical phone (auto-labeler
   ran two models and didn't always merge candidates below its own 0.5 IoU threshold - a nested
   box pair can have IoU well under 0.5 while one is still ~90-100% contained inside the other).
   Merged via "intersection over the smaller box's area" (IoS), not IoU - real-data check showed a
   strong bimodal split (66% of pairs at IoS~1.0, a real duplicate signal) vs a genuinely separate
   tail below ~0.8, so IOS_THRESHOLD=0.85 catches true duplicates without merging distinct boxes.
   Keeps the larger box in each merged cluster (no confidence score survives in saved YOLO labels).

Writes to a separate output dir rather than overwriting subject01_phonewin_review/ in place, so the
result can be spot-checked again before merging into annotation_batch/.

Usage: ../../.venv/Scripts/python.exe fix_subject01_review_boxes.py
"""
import os
import shutil

REVIEW_DIR = os.path.join(os.path.dirname(__file__), "datasets", "oep-msu", "subject01_phonewin_review")
OUT_DIR = os.path.join(os.path.dirname(__file__), "datasets", "oep-msu", "subject01_phonewin_fixed")

BACKGROUND_MAX_CX = 0.55  # confirmed gap: no real phone box has cx in [0.5211, 0.5850]
IOS_MERGE_THRESHOLD = 0.85

PHONE_CLASS = "0"


def box_xyxy(cx, cy, w, h):
    return cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2


def overlap_ratio(a, b):
    ax1, ay1, ax2, ay2 = box_xyxy(*a)
    bx1, by1, bx2, by2 = box_xyxy(*b)
    ix1, iy1 = max(ax1, bx1), max(ay1, by1)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    if ix2 <= ix1 or iy2 <= iy1:
        return 0.0
    inter = (ix2 - ix1) * (iy2 - iy1)
    area_a = (ax2 - ax1) * (ay2 - ay1)
    area_b = (bx2 - bx1) * (by2 - by1)
    return inter / min(area_a, area_b)


def merge_duplicates(boxes):
    # boxes: list of (cx, cy, w, h). Keep larger-area box in each nested/duplicate cluster.
    boxes = sorted(boxes, key=lambda b: -(b[2] * b[3]))
    kept = []
    for cand in boxes:
        if all(overlap_ratio(cand, k) < IOS_MERGE_THRESHOLD for k in kept):
            kept.append(cand)
    return kept


def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    txt_files = sorted(f for f in os.listdir(REVIEW_DIR) if f.endswith(".txt") and f != "classes.txt")

    dropped_background = 0
    merged_duplicates = 0
    frames_touched = 0

    for fname in txt_files:
        src_path = os.path.join(REVIEW_DIR, fname)
        with open(src_path) as f:
            lines = [l.split() for l in f if l.strip()]

        phone_boxes = []
        other_lines = []
        for parts in lines:
            if parts[0] == PHONE_CLASS:
                cx, cy, w, h = map(float, parts[1:])
                phone_boxes.append((cx, cy, w, h))
            else:
                other_lines.append(parts)

        before_count = len(phone_boxes)
        phone_boxes = [b for b in phone_boxes if b[0] >= BACKGROUND_MAX_CX]
        dropped_background += before_count - len(phone_boxes)

        before_merge = len(phone_boxes)
        phone_boxes = merge_duplicates(phone_boxes)
        merged_duplicates += before_merge - len(phone_boxes)

        if before_count != len(phone_boxes) or before_merge != len(phone_boxes):
            frames_touched += 1

        out_lines = [f"{PHONE_CLASS} {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}" for cx, cy, w, h in phone_boxes]
        out_lines += [" ".join(parts) for parts in other_lines]

        out_path = os.path.join(OUT_DIR, fname)
        with open(out_path, "w") as f:
            if out_lines:
                f.write("\n".join(out_lines) + "\n")

    # classes.txt + images copied alongside so the folder is self-contained for a re-check in LabelImg.
    shutil.copy(os.path.join(REVIEW_DIR, "classes.txt"), os.path.join(OUT_DIR, "classes.txt"))
    for fname in os.listdir(REVIEW_DIR):
        if fname.endswith(".jpg"):
            shutil.copy(os.path.join(REVIEW_DIR, fname), os.path.join(OUT_DIR, fname))

    print(f"{len(txt_files)} label files processed, {frames_touched} changed")
    print(f"  {dropped_background} background false-positive boxes dropped")
    print(f"  {merged_duplicates} duplicate/nested boxes merged away")
    print(f"\nFixed output written to {OUT_DIR}")


if __name__ == "__main__":
    main()
