"""Remove mislabeled phone boxes from datasets/oep-msu/frozen_holdout/.

WHY THIS EXISTS
The fairness audit of 2026-08-01 found the OEP rig's second camera - a small chrome camcorder on a
stand, with a visible cable, sitting beside the subject's head - had been annotated as class 0
"phone" across the corpus, and fixed it (579 boxes, 11 subjects). That fix was applied to
`annotation_batch/`. The frozen holdout lives PHYSICALLY OUTSIDE annotation_batch precisely so no
training-side script can touch it - so the correction never propagated into it, and the holdout has
carried the defect ever since.

Found 2026-09-08 while diagnosing why three consecutive retrains all "regressed" the holdout. The
false negatives were not spread across conditions: subject01's plain-frame batch scored 16/16
missed (recall 0.00) while the SAME subject's phonewin frames scored 30/30. Pulling the images
showed why - those 16 frames contain no phone at all. The holdout was scoring the model as wrong
for correctly detecting nothing, and the only way to "improve" on those frames was to start firing
on a tripod-mounted camera.

WHAT IS REMOVED - 41 class-0 boxes, each verified by direct visual inspection of a padded crop
(the same discipline that worked in apply_phone_label_corrections.py; positional/aspect heuristics
were tried here first and do NOT separate the two objects, because the rig was repositioned between
sessions):
  * 35 boxes drawn on the chrome camera device (chrome body, round lens, red LED, cable)
  * 4 oversized junk boxes covering >10% of the frame (subject01 x2, subject24 x2)
  * 2 tiny junk boxes: one on an eyeglasses lens (subject06), one on blank wall (subject01)
Real phones - a dark or silver slab gripped by fingers at the ear, aspect ratio ~2-3.5 - are kept.
The distinction is unambiguous in the crops; the hit frames prove it, carrying two boxes, one on
the device and one on the genuine phone.

20 frames lose every phone box and become verified phone-NEGATIVE. Their face boxes are untouched,
so the files are not empty - they are correctly-labeled negatives, which is what they always were.

This CHANGES REPORTED METRICS in both directions: it lifts recall (frames that were unwinnable stop
counting as misses) and it can lower precision (subject24_phonewin_0293.40s was being scored a true
positive for a 0.46-confidence box on the device; with no real phone there, that is a false
positive, and it should count as one).

Backs up every label file before writing. Dry-run by default.

Usage:
  ../.venv/Scripts/python.exe fix_frozen_holdout_device_labels.py           # dry run
  ../.venv/Scripts/python.exe fix_frozen_holdout_device_labels.py --apply
  ../.venv/Scripts/python.exe fix_frozen_holdout_device_labels.py --restore # undo from backup
"""
import argparse
import os
import shutil

HERE = os.path.dirname(__file__)
HOLDOUT = os.path.join(HERE, "datasets", "oep-msu", "frozen_holdout")
BACKUP = os.path.join(HERE, "datasets", "oep-msu", "frozen_holdout_label_backup")

PHONE_CLASS = "0"

# {label file stem: [indices into that frame's class-0 boxes, in file order, to delete]}
# Verified individually against padded crops rendered at 300px - see module docstring.
REMOVE = {
    # --- subject01: every phone box in this batch is the device or junk; no phone is present ---
    "subject01_frame00113": [0],
    "subject01_frame00125": [0],
    "subject01_frame00180": [0],
    "subject01_frame00201": [0],
    "subject01_frame00207": [0],
    "subject01_frame00208": [0],
    "subject01_frame00219": [0],
    "subject01_frame00489": [0],
    "subject01_frame00520": [0],
    "subject01_frame00551": [0, 1],
    "subject01_frame00579": [0],
    "subject01_frame00602": [0],
    "subject01_frame00613": [0],
    "subject01_frame00630": [0],
    "subject01_frame00657": [0],
    "subject01_frame00719": [0],
    # --- subject06: device + junk boxes only; genuine phone boxes in this batch are kept ---
    "subject06_phonewin_0310.20s": [0],
    "subject06_phonewin_0310.40s": [0],
    "subject06_phonewin_0312.80s": [0],
    "subject06_phonewin_0314.60s": [0, 1],
    "subject06_phonewin_0318.00s": [0],
    "subject06_phonewin_1025.40s": [0],
    "subject06_phonewin_1026.00s": [0],
    "subject06_phonewin_1031.80s": [1],
    # --- subject24: device + two torso-sized junk boxes; genuine phone boxes kept ---
    "subject24_phonewin_0293.40s": [0],
    "subject24_phonewin_0295.20s": [1],
    "subject24_phonewin_0300.60s": [1],
    "subject24_phonewin_0301.00s": [1],
    "subject24_phonewin_0301.60s": [1],
    "subject24_phonewin_0302.00s": [1],
    "subject24_phonewin_0304.40s": [1],
    "subject24_phonewin_0307.80s": [1],
    "subject24_phonewin_0313.80s": [2],
    "subject24_phonewin_0314.20s": [2],
    "subject24_phonewin_0316.60s": [1],
    "subject24_phonewin_0317.40s": [1],
    "subject24_phonewin_0317.80s": [1],
    "subject24_phonewin_0319.00s": [2],
    "subject24_phonewin_0322.40s": [2],
}


def load(stem):
    path = os.path.join(HOLDOUT, stem + ".txt")
    with open(path) as f:
        return path, [ln.rstrip("\n") for ln in f if ln.strip()]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="write changes (default: dry run)")
    ap.add_argument("--restore", action="store_true", help="restore label files from backup")
    args = ap.parse_args()

    if args.restore:
        if not os.path.isdir(BACKUP):
            raise SystemExit(f"no backup at {BACKUP}")
        n = 0
        for f in os.listdir(BACKUP):
            shutil.copy2(os.path.join(BACKUP, f), os.path.join(HOLDOUT, f))
            n += 1
        print(f"restored {n} label files from {BACKUP}")
        return

    if args.apply:
        if os.path.isdir(BACKUP):
            print(f"backup already exists at {BACKUP} - leaving it (it is the pre-fix state)")
        else:
            os.makedirs(BACKUP)
            for f in os.listdir(HOLDOUT):
                if f.endswith(".txt"):
                    shutil.copy2(os.path.join(HOLDOUT, f), os.path.join(BACKUP, f))
            print(f"backed up label files -> {BACKUP}")

    removed = 0
    emptied = []
    missing = []
    for stem, drop_idx in sorted(REMOVE.items()):
        path = os.path.join(HOLDOUT, stem + ".txt")
        if not os.path.exists(path):
            missing.append(stem)
            continue
        _, lines = load(stem)
        phone_positions = [i for i, ln in enumerate(lines) if ln.split()[0] == PHONE_CLASS]
        to_delete = {phone_positions[k] for k in drop_idx if k < len(phone_positions)}
        kept = [ln for i, ln in enumerate(lines) if i not in to_delete]
        removed += len(to_delete)
        if not any(ln.split()[0] == PHONE_CLASS for ln in kept):
            emptied.append(stem)
        if args.apply:
            with open(path, "w") as f:
                f.write("\n".join(kept) + ("\n" if kept else ""))

    print(f"\n{'APPLIED' if args.apply else 'DRY RUN'}: "
          f"{removed} mislabeled phone boxes across {len(REMOVE)} frames")
    print(f"  {len(emptied)} frames lose every phone box -> now verified phone-NEGATIVE")
    for s in emptied:
        print(f"      {s}")
    if missing:
        print(f"  WARNING: {len(missing)} listed frames not found: {missing}")
    if not args.apply:
        print("\nre-run with --apply to write. Then re-run evaluate_frozen_holdout.py to re-baseline.")


if __name__ == "__main__":
    main()
