"""Turn the raw downloaded Kaggle cell-phone dataset into YOLO's expected train/val layout
and write a data.yaml for it. Run after download_dataset.py.

Handles either a flat directory of paired image/.txt files, or pre-split images/ + labels/
subdirectories - whichever the Kaggle download actually contains.

Usage: ../../.venv/Scripts/python.exe prepare_dataset.py
"""
import os
import random
import shutil

RAW_DIR = os.path.join(os.path.dirname(__file__), "datasets", "cell-phone-kaggle")
OUT_DIR = os.path.join(os.path.dirname(__file__), "datasets", "cell-phone-yolo")
VAL_FRACTION = 0.15
SEED = 42
IMAGE_EXTS = (".jpg", ".jpeg", ".png")


def find_image_label_pairs(raw_dir):
    images_by_stem = {}
    labels_by_stem = {}
    for root, _dirs, files in os.walk(raw_dir):
        for f in files:
            stem, ext = os.path.splitext(f)
            full = os.path.join(root, f)
            if ext.lower() in IMAGE_EXTS:
                images_by_stem[stem] = full
            elif ext.lower() == ".txt" and stem.lower() != "classes":
                labels_by_stem[stem] = full

    pairs = [
        (images_by_stem[stem], labels_by_stem[stem])
        for stem in images_by_stem
        if stem in labels_by_stem
    ]
    return pairs


def main():
    if not os.path.isdir(RAW_DIR):
        raise SystemExit(f"{RAW_DIR} not found - run download_dataset.py first.")

    pairs = find_image_label_pairs(RAW_DIR)
    if not pairs:
        raise SystemExit(
            f"No matching image/.txt label pairs found under {RAW_DIR}. "
            "Inspect the folder structure and adjust this script if the dataset layout differs."
        )

    class_ids = set()
    for _img_path, lbl_path in pairs:
        with open(lbl_path) as f:
            for line in f:
                line = line.strip()
                if line:
                    class_ids.add(int(line.split()[0]))
    class_ids = sorted(class_ids)
    if len(class_ids) == 1:
        # This script is single-purpose (phone-specialist fine-tuning, see finetune_phone.py),
        # so a single-class dataset is assumed to be "phone" regardless of its raw label id -
        # confirmed for the Kaggle samuelayman/cell-phone set (all 1000 labels use id 40, no
        # classes.txt shipped, but the dataset is titled "Cell phone" and every file matches).
        names = ["phone"]
    else:
        names = [f"class_{i}" for i in class_ids]
        print(
            f"WARNING: label files use multiple class ids {class_ids} - this script assumes a "
            f"single-class phone dataset. Generated generic names {names}; check {RAW_DIR} for "
            "a classes.txt/README to confirm the real class mapping before trusting results."
        )

    # YOLO requires label class ids to be contiguous 0-indexed values matching position in
    # `names`, but the raw files use their own (possibly non-zero) ids - e.g. this Kaggle set
    # uses "40" throughout. Remap on write rather than copying the raw .txt bytes verbatim.
    remap = {old_id: new_id for new_id, old_id in enumerate(class_ids)}

    def write_remapped_label(src_path, dst_path):
        with open(src_path) as f:
            lines = f.readlines()
        with open(dst_path, "w") as f:
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                parts = line.split()
                parts[0] = str(remap[int(parts[0])])
                f.write(" ".join(parts) + "\n")

    random.seed(SEED)
    random.shuffle(pairs)
    split_idx = int(len(pairs) * (1 - VAL_FRACTION))
    train_pairs, val_pairs = pairs[:split_idx], pairs[split_idx:]

    for split_name, split_pairs in (("train", train_pairs), ("val", val_pairs)):
        img_dir = os.path.join(OUT_DIR, "images", split_name)
        lbl_dir = os.path.join(OUT_DIR, "labels", split_name)
        os.makedirs(img_dir, exist_ok=True)
        os.makedirs(lbl_dir, exist_ok=True)
        for img_path, lbl_path in split_pairs:
            shutil.copy2(img_path, os.path.join(img_dir, os.path.basename(img_path)))
            write_remapped_label(lbl_path, os.path.join(lbl_dir, os.path.basename(lbl_path)))

    data_yaml_path = os.path.join(OUT_DIR, "data.yaml")
    names_yaml = "[" + ", ".join(f"'{n}'" for n in names) + "]"
    with open(data_yaml_path, "w") as f:
        f.write(
            f"train: {os.path.join(OUT_DIR, 'images', 'train')}\n"
            f"val: {os.path.join(OUT_DIR, 'images', 'val')}\n"
            f"nc: {len(names)}\n"
            f"names: {names_yaml}\n"
        )

    print(f"{len(train_pairs)} train / {len(val_pairs)} val images written to {OUT_DIR}")
    print(f"data.yaml written to {data_yaml_path}")


if __name__ == "__main__":
    main()
