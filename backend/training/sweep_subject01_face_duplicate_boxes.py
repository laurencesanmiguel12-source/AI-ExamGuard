"""Full-subject01 sweep for the face-duplicate-box defect `fix_subject01_face_duplicate_boxes.py`
found and fixed, but only within the 232-frame subject01_phonewin_review/ batch (its PREFIX is
hardcoded to "subject01_phonewin_"). That defect - an auto-labeler "phone" box that's actually a
near-duplicate (IoS > 0.85) of the face box, not a real phone - was never checked against the rest
of subject01's frames (the older subject01_frame* sequence, 164 files) or re-checked after today's
per-frame device-confounder sweep (fix_subjects_01_06_09_24_phone_labels.py) changed which phone
boxes are even present. Same overlap logic, just widened to every subject01_*.txt file rather than
one filename prefix.

Usage: ../.venv/Scripts/python.exe sweep_subject01_face_duplicate_boxes.py           (dry run)
       ../.venv/Scripts/python.exe sweep_subject01_face_duplicate_boxes.py --apply    (fixes in place)
"""
import os
import sys

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OEP_DIR = os.path.join(BACKEND_DIR, "training", "datasets", "oep-msu")
ANNOTATION_BATCH_DIR = os.path.join(OEP_DIR, "annotation_batch")
TRAIN_LABELS_DIR = os.path.join(OEP_DIR, "split", "train", "labels")
REVIEW_OUT_DIR = os.path.join(OEP_DIR, "subject01_full_facedup_review")

IOS_THRESHOLD = 0.85
PHONE_CLASS = "0"
FACE_CLASS = "1"
PREFIX = "subject01_"


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


def fix_lines(lines):
    """Return (fixed_lines, dropped_count) with face-duplicate phone boxes removed."""
    phones, faces, other = [], [], []
    for parts in lines:
        if parts[0] == PHONE_CLASS:
            phones.append(tuple(map(float, parts[1:])))
        elif parts[0] == FACE_CLASS:
            faces.append(tuple(map(float, parts[1:])))
            other.append(parts)
        else:
            other.append(parts)

    kept_phones = [
        p for p in phones
        if all(overlap_ratio(p, f) < IOS_THRESHOLD for f in faces)
    ]
    dropped = len(phones) - len(kept_phones)

    out_lines = [f"{PHONE_CLASS} {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}" for cx, cy, w, h in kept_phones]
    out_lines += [" ".join(parts) for parts in other]
    return out_lines, dropped


def process_dir(src_dir, dst_dir, in_place):
    if not os.path.isdir(src_dir):
        return [], [], 0

    txt_files = sorted(
        f for f in os.listdir(src_dir)
        if f.startswith(PREFIX) and f.endswith(".txt")
    )

    total_dropped = 0
    files_touched = []
    for fname in txt_files:
        src_path = os.path.join(src_dir, fname)
        with open(src_path) as f:
            lines = [l.split() for l in f if l.strip()]

        fixed_lines, dropped = fix_lines(lines)
        if dropped:
            total_dropped += dropped
            files_touched.append((fname, dropped))

        out_path = os.path.join(dst_dir, fname) if not in_place else src_path
        if dropped or not in_place:
            os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
            with open(out_path, "w") as f:
                if fixed_lines:
                    f.write("\n".join(fixed_lines) + "\n")

    return txt_files, files_touched, total_dropped


def main():
    apply = "--apply" in sys.argv

    if not apply:
        os.makedirs(REVIEW_OUT_DIR, exist_ok=True)
        txt_files, touched, dropped = process_dir(ANNOTATION_BATCH_DIR, REVIEW_OUT_DIR, in_place=False)
        print(f"DRY RUN - fixed labels written to {REVIEW_OUT_DIR} for spot-check")
        print(f"{len(txt_files)} subject01_* files scanned in annotation_batch/")
        print(f"{len(touched)} files had a face-duplicate phone box dropped, {dropped} boxes total:")
        for fname, n in touched:
            print(f"  {fname}: {n} dropped")
        print("\nRe-run with --apply once these look right to fix annotation_batch/ and split/train/labels/ in place.")
        return

    for label, src_dir in (("annotation_batch/", ANNOTATION_BATCH_DIR), ("split/train/labels/", TRAIN_LABELS_DIR)):
        txt_files, touched, dropped = process_dir(src_dir, src_dir, in_place=True)
        print(f"{label}: {len(txt_files)} files scanned, {len(touched)} fixed, {dropped} boxes dropped")
        for fname, n in touched:
            print(f"  {fname}: {n} dropped")


if __name__ == "__main__":
    main()
