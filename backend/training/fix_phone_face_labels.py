"""One-off cleanup for the reorganized_phone_dataset_yolo label files (see
backend/training/datasets/phone-face-yolo/data.yaml), fixing the two real problems found by a
full-dataset scan:

1. 242 label files have two or three box annotations concatenated onto a single line (10 or 15
   space-separated fields instead of 5) - almost certainly a lost newline somewhere upstream.
   Every case scanned split evenly into N valid 5-field boxes, so this splits them back out
   rather than dropping the line.
2. 2 label files have a garbage line (zero width/height, out-of-range center) that isn't
   recoverable - those lines are dropped.

Deliberately NOT touched: ~1,112 lines where a box edge extends slightly past the image bound
(nearly all by <=0.02, floating-point-rounding-sized). Ultralytics clips these to [0,1] itself at
train time, so "fixing" them here would just be guessing at the annotator's intent.

Backs up every file it modifies (original bytes, untouched) under
backend/training/datasets/phone-face-yolo/label_fix_backup/ before writing, mirroring the
dataset's split/labels structure, since the source dataset lives outside the repo and isn't
under version control.

Usage: ../../.venv/Scripts/python.exe fix_phone_face_labels.py
"""
import os
import shutil

BASE = r"C:\baidunetdiskdownload\reorganized_phone_dataset_yolo\reorganized_dataset"
SPLITS = ("train", "val", "test")
VALID_CLASSES = {0, 1}
BACKUP_DIR = os.path.join(
    os.path.dirname(__file__), "datasets", "phone-face-yolo", "label_fix_backup"
)


def is_valid_box(parts):
    if len(parts) != 5:
        return False

    cls_raw, cx_raw, cy_raw, w_raw, h_raw = parts
    if not cls_raw.lstrip("-").isdigit() or int(cls_raw) not in VALID_CLASSES:
        return False

    try:
        cx, cy, w, h = float(cx_raw), float(cy_raw), float(w_raw), float(h_raw)
    except ValueError:
        return False

    return w > 0 and h > 0 and 0.0 <= cx <= 1.0 and 0.0 <= cy <= 1.0


def fix_file(path):
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        raw_lines = f.readlines()

    out_lines = []
    changed = False
    dropped = 0
    recovered = 0

    for raw in raw_lines:
        line = raw.strip()
        if not line:
            continue
        parts = line.split()

        if len(parts) == 5:
            if is_valid_box(parts):
                out_lines.append(" ".join(parts))
            else:
                changed = True
                dropped += 1
            continue

        if len(parts) % 5 == 0 and len(parts) > 5:
            groups = [parts[i:i + 5] for i in range(0, len(parts), 5)]
            for g in groups:
                if is_valid_box(g):
                    out_lines.append(" ".join(g))
                    recovered += 1
                else:
                    dropped += 1
            changed = True
            continue

        out_lines.append(line)

    if changed:
        backup_path = os.path.join(BACKUP_DIR, os.path.relpath(path, BASE))
        os.makedirs(os.path.dirname(backup_path), exist_ok=True)
        shutil.copy2(path, backup_path)
        with open(path, "w", encoding="utf-8") as f:
            for line in out_lines:
                f.write(line + "\n")

    return changed, dropped, recovered


def main():
    files_changed = 0
    total_dropped = 0
    total_recovered = 0

    for split in SPLITS:
        lbl_dir = os.path.join(BASE, split, "labels")
        for fname in sorted(os.listdir(lbl_dir)):
            if not fname.endswith(".txt"):
                continue
            changed, dropped, recovered = fix_file(os.path.join(lbl_dir, fname))
            if changed:
                files_changed += 1
                total_dropped += dropped
                total_recovered += recovered

    print(f"\nFiles changed: {files_changed}")
    print(f"Garbage lines dropped: {total_dropped}")
    print(f"Boxes recovered from merged lines: {total_recovered}")
    print(f"Originals backed up to: {BACKUP_DIR}")


if __name__ == "__main__":
    main()
