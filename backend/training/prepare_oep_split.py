"""Split the manually-annotated OEP batch (datasets/oep-msu/annotation_batch/) into a
YOLO-standard train/val layout (images/ + labels/ siblings), so it can be added alongside the
external reorganized_phone_dataset_yolo set in phone-face-yolo/data.yaml.

Split by SUBJECT, not by individual frame - frames from the same subject share the same face,
room, and camera angle, so a per-frame random split would leak near-duplicate context between
train and val and inflate val metrics. VAL_SUBJECTS is a fixed, deliberate choice (not random)
covering one phone-heavy actor subject (09) and one real-exam subject (11), so val still has some
genuine phone-positive examples and some non-actor footage, while keeping most data in train.

Frames with a face box but no phone box are kept as-is (real negatives - reviewed and confirmed
phone-free). Frames with neither box get an empty .txt written explicitly, so they're unambiguous
verified negatives rather than "forgot to label."

Usage: ../.venv/Scripts/python.exe prepare_oep_split.py
"""
import os
import shutil

BATCH_DIR = os.path.join(os.path.dirname(__file__), "datasets", "oep-msu", "annotation_batch")
SPLIT_DIR = os.path.join(os.path.dirname(__file__), "datasets", "oep-msu", "split")

VAL_SUBJECTS = {"subject09", "subject11"}


def main():
    image_files = sorted(f for f in os.listdir(BATCH_DIR) if f.lower().endswith(".jpg"))

    for split in ("train", "val"):
        os.makedirs(os.path.join(SPLIT_DIR, split, "images"), exist_ok=True)
        os.makedirs(os.path.join(SPLIT_DIR, split, "labels"), exist_ok=True)

    counts = {"train": 0, "val": 0}
    empty_labels_written = 0

    for fname in image_files:
        subject = fname.split("_")[0]
        split = "val" if subject in VAL_SUBJECTS else "train"

        src_img = os.path.join(BATCH_DIR, fname)
        dst_img = os.path.join(SPLIT_DIR, split, "images", fname)
        shutil.copy2(src_img, dst_img)

        label_name = os.path.splitext(fname)[0] + ".txt"
        src_label = os.path.join(BATCH_DIR, label_name)
        dst_label = os.path.join(SPLIT_DIR, split, "labels", label_name)
        if os.path.exists(src_label):
            shutil.copy2(src_label, dst_label)
        else:
            open(dst_label, "w").close()
            empty_labels_written += 1

        counts[split] += 1

    print(f"train: {counts['train']} images -> {os.path.join(SPLIT_DIR, 'train')}")
    print(f"val:   {counts['val']} images -> {os.path.join(SPLIT_DIR, 'val')} (subjects: {sorted(VAL_SUBJECTS)})")
    print(f"{empty_labels_written} frames had no boxes at all - wrote empty label files for them")


if __name__ == "__main__":
    main()
