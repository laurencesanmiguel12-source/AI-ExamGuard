"""Merges the AI-corrected personal_phone_video_review/ batch into annotation_batch/, following
this project's standing discipline that new sources always land in an isolated review folder first
and only get merged into the shared annotation_batch/ once reviewed (see
prepare_personal_phone_video_review.py's docstring for why - a prior auto-labeler run nearly
clobbered already-reviewed ground truth once). Review here was an AI-assisted visual pass
(apply_phone_label_corrections.py) rather than manual LabelImg, per explicit user instruction.

Filenames are prefixed `personal_video_review_*`, distinct from every existing `subjectNN_*` OEP
name, so this is a pure copy with zero collision risk (checked before running). Frames are treated
as one subject ("personal") for prepare_oep_split.py's subject-based split - not in VAL_SUBJECTS,
so all go to train, which is correct here since this is supplementary phone-positive/negative data
for train, not new val diversity.

Usage: ../../.venv/Scripts/python.exe merge_personal_video_review.py [--apply]
"""
import glob
import os
import shutil
import sys

SRC_DIR = os.path.join(os.path.dirname(__file__), "datasets", "oep-msu", "personal_phone_video_review")
DST_DIR = os.path.join(os.path.dirname(__file__), "datasets", "oep-msu", "annotation_batch")


def main():
    apply = "--apply" in sys.argv
    pairs = sorted(glob.glob(os.path.join(SRC_DIR, "personal_video_review_*.jpg")))

    collisions = [p for p in pairs if os.path.exists(os.path.join(DST_DIR, os.path.basename(p)))]
    if collisions:
        raise SystemExit(f"ABORT: {len(collisions)} filename collisions with annotation_batch/, e.g. {collisions[0]}")

    print(f"{len(pairs)} images to merge from {SRC_DIR} -> {DST_DIR}")
    if not apply:
        print("DRY RUN - pass --apply to actually copy")
        return

    copied = 0
    for img_path in pairs:
        name = os.path.basename(img_path)
        label_path = img_path.replace(".jpg", ".txt")
        shutil.copy2(img_path, os.path.join(DST_DIR, name))
        if os.path.exists(label_path):
            shutil.copy2(label_path, os.path.join(DST_DIR, os.path.basename(label_path)))
        else:
            open(os.path.join(DST_DIR, os.path.basename(label_path)), "w").close()
        copied += 1

    print(f"Merged {copied} image+label pairs into {DST_DIR}")


if __name__ == "__main__":
    main()
