"""Download the samuelayman/cell-phone Kaggle dataset for phone-detection fine-tuning.

Requires Kaggle API credentials: either a ~/.kaggle/kaggle.json file (Account -> Create New
Token on kaggle.com), or the KAGGLE_USERNAME / KAGGLE_KEY environment variables set.

Usage: ../../.venv/Scripts/python.exe download_dataset.py
"""
import os
import sys

DATASET = "samuelayman/cell-phone"
DEST = os.path.join(os.path.dirname(__file__), "datasets", "cell-phone-kaggle")

if __name__ == "__main__":
    try:
        from kaggle.api.kaggle_api_extended import KaggleApi
    except OSError as e:
        print(f"Kaggle credentials not found or invalid: {e}")
        print("Set up ~/.kaggle/kaggle.json (from kaggle.com -> Account -> Create New Token)")
        print("or set KAGGLE_USERNAME and KAGGLE_KEY environment variables.")
        sys.exit(1)

    api = KaggleApi()
    api.authenticate()

    os.makedirs(DEST, exist_ok=True)
    print(f"Downloading {DATASET} to {DEST} ...")
    api.dataset_download_files(DATASET, path=DEST, unzip=True)

    print("Done. Contents:")
    for root, dirs, files in os.walk(DEST):
        depth = root.replace(DEST, "").count(os.sep)
        indent = "  " * depth
        print(f"{indent}{os.path.basename(root) or '.'}/  ({len(files)} files)")
        if depth < 2 and files:
            for f in files[:3]:
                print(f"{indent}  {f}")
            if len(files) > 3:
                print(f"{indent}  ... and {len(files) - 3} more")
