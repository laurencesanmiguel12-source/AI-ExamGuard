"""Assemble a curated, flat folder for manual annotation from the OEP frame_priority.csv manifest
(see prioritize_oep_frames.py / extract_oep_phone_windows.py). Pulls a bounded, less-redundant
subset rather than handing the annotator all ~9.7k raw frames:

- ALL 'phone' frames kept (the scarce resource - even near-duplicate frames within one burst still
  show slightly different hand/phone position, which is real variety, not pure waste).
- 'other_cheat' frames downsampled to roughly 2x the phone count, spread evenly per-subject
  (not randomly across the whole pool) so no single long session dominates the batch.
- 'clean' frames downsampled to roughly 15% of the batch total, for negative examples.

Output filenames are unchanged from raw_frames/ (they already encode subject + timestamp), copied
into one flat folder so an annotation tool like LabelImg can just be pointed at a single directory.
Keeping the original filenames also preserves per-subject traceability for a later leakage-safe
train/val split (see earlier discussion on splitting by session, not by individual frame).

Usage: ../../.venv/Scripts/python.exe build_annotation_batch.py
"""
import csv
import os
import random
import shutil

MANIFEST = os.path.join(os.path.dirname(__file__), "datasets", "oep-msu", "frame_priority.csv")
OUT_DIR = os.path.join(os.path.dirname(__file__), "datasets", "oep-msu", "annotation_batch")
SEED = 42


def stratified_sample(rows, target_count, seed):
    by_subject = {}
    for r in rows:
        by_subject.setdefault(r["subject"], []).append(r)

    rng = random.Random(seed)
    per_subject_target = max(1, target_count // len(by_subject))
    selected = []
    for subject, subject_rows in by_subject.items():
        subject_rows = sorted(subject_rows, key=lambda r: float(r["time_sec"]))
        if len(subject_rows) <= per_subject_target:
            selected.extend(subject_rows)
        else:
            step = len(subject_rows) / per_subject_target
            selected.extend(subject_rows[int(i * step)] for i in range(per_subject_target))
    rng.shuffle(selected)
    return selected


def main():
    with open(MANIFEST) as f:
        rows = list(csv.DictReader(f))

    by_priority = {"phone": [], "other_cheat": [], "clean": []}
    for r in rows:
        by_priority[r["priority"]].append(r)

    phone_rows = by_priority["phone"]
    other_target = min(len(by_priority["other_cheat"]), len(phone_rows) * 2)
    other_rows = stratified_sample(by_priority["other_cheat"], other_target, SEED)

    batch_so_far = len(phone_rows) + len(other_rows)
    clean_target = min(len(by_priority["clean"]), int(batch_so_far * 0.15))
    clean_rows = stratified_sample(by_priority["clean"], clean_target, SEED + 1)

    os.makedirs(OUT_DIR, exist_ok=True)
    copied = 0
    for r in phone_rows + other_rows + clean_rows:
        src = r["frame_path"]
        dst = os.path.join(OUT_DIR, os.path.basename(src))
        if not os.path.exists(dst):
            shutil.copy2(src, dst)
        copied += 1

    print(f"phone: {len(phone_rows)}")
    print(f"other_cheat: {len(other_rows)} (of {len(by_priority['other_cheat'])} available)")
    print(f"clean: {len(clean_rows)} (of {len(by_priority['clean'])} available)")
    print(f"\n{copied} frames copied to {OUT_DIR}")


if __name__ == "__main__":
    main()
