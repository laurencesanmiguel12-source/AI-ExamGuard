"""Redo the personal_phone_video_review/ merge into annotation_batch/ at a downweighted sample
size, after the first full-1773-frame merge (merge_personal_video_review.py) turned out to REGRESS
the frozen holdout eval (presence f1 0.833 vs production's 0.854, FP 9 vs 6) despite looking fine
on training-time val metrics. Root cause found by inspecting per-subject frame counts in
annotation_batch/: "personal" contributed 1773 frames, ~5x the single largest existing OEP subject
(subject01, 362) and dwarfing every other subject - one person/background/lighting setup was
massively overrepresented relative to the rest of the dataset's diversity, a plausible cause of the
aggregate regression even though the specific face-anchored-FP bug it targeted lives in that same
overrepresented data.

Downweights to TARGET_COUNT (360, matching subject01's scale - the largest existing subject, so
personal video doesn't out-represent anything else) via even time-stride sampling across the full
1773-frame corrected set. Stride sampling (not random) preserves temporal spread across the whole
~117s video, which also naturally preserves the corrected phone-present/absent mix (44%/56%) since
phone appearances are spread throughout, not clustered.

First REMOVES every existing personal_video_review_* pair from annotation_batch/ (the full-1773
merge), then copies only the downweighted sample back in - a clean re-merge, not an additive one.

Usage: ../../.venv/Scripts/python.exe reweight_personal_video_merge.py [--apply] [--target 360]
"""
import glob
import os
import shutil
import sys

SRC_DIR = os.path.join(os.path.dirname(__file__), "datasets", "oep-msu", "personal_phone_video_review")
DST_DIR = os.path.join(os.path.dirname(__file__), "datasets", "oep-msu", "annotation_batch")
TARGET_COUNT = 360


def main():
    apply = "--apply" in sys.argv
    target = TARGET_COUNT
    for i, arg in enumerate(sys.argv):
        if arg == "--target" and i + 1 < len(sys.argv):
            target = int(sys.argv[i + 1])

    existing = sorted(glob.glob(os.path.join(DST_DIR, "personal_video_review_*.jpg")))
    all_frames = sorted(glob.glob(os.path.join(SRC_DIR, "personal_video_review_*.jpg")))
    stride = max(1, len(all_frames) // target)
    sampled = all_frames[::stride][:target]

    has_phone = 0
    for img_path in sampled:
        label_path = img_path.replace(".jpg", ".txt")
        if os.path.exists(label_path) and any(
            line.split() and line.split()[0] == "0" for line in open(label_path)
        ):
            has_phone += 1

    print(f"currently merged: {len(existing)} personal frames in annotation_batch/")
    print(f"source pool: {len(all_frames)} corrected frames, stride={stride}")
    print(f"downweighted sample: {len(sampled)} frames ({has_phone} phone-positive, {len(sampled) - has_phone} phone-negative)")

    if not apply:
        print("DRY RUN - pass --apply to remove the old merge and copy in the downweighted sample")
        return

    for img_path in existing:
        os.remove(img_path)
        label_path = img_path.replace(".jpg", ".txt")
        if os.path.exists(label_path):
            os.remove(label_path)
    print(f"Removed {len(existing)} previously-merged personal frames from annotation_batch/")

    copied = 0
    for img_path in sampled:
        name = os.path.basename(img_path)
        label_path = img_path.replace(".jpg", ".txt")
        shutil.copy2(img_path, os.path.join(DST_DIR, name))
        if os.path.exists(label_path):
            shutil.copy2(label_path, os.path.join(DST_DIR, os.path.basename(label_path)))
        else:
            open(os.path.join(DST_DIR, os.path.basename(label_path)), "w").close()
        copied += 1
    print(f"Merged downweighted sample: {copied} image+label pairs into {DST_DIR}")


if __name__ == "__main__":
    main()
