"""Fine-tune a phone-detection specialist on top of the existing yolov8s.pt COCO weights.

Deliberately trains a SEPARATE single-class model rather than overwriting
app/resources/yolov8s.pt in place: the Kaggle dataset only labels "phone", and fine-tuning
directly on a 1-class dataset rebuilds YOLO's detection head to output just that one class,
which would silently delete the "person" class the app's MULTIPLE_PEOPLE check depends on
(see object_detection_service.py). Run this model as a second inference pass alongside the
untouched yolov8s.pt, not as a replacement for it.

Usage: ../../.venv/Scripts/python.exe finetune_phone.py [--epochs 30] [--batch 8] [--imgsz 640]
"""
import argparse
import os

from ultralytics import YOLO

BASE_WEIGHTS = os.path.join(
    os.path.dirname(__file__), "..", "app", "resources", "yolov8s.pt"
)
DATA_YAML = os.path.join(
    os.path.dirname(__file__), "datasets", "cell-phone-yolo", "data.yaml"
)
RUNS_DIR = os.path.join(os.path.dirname(__file__), "runs")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--epochs", type=int, default=30)
    parser.add_argument("--batch", type=int, default=8)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--patience", type=int, default=8, help="early-stop patience")
    args = parser.parse_args()

    if not os.path.isfile(DATA_YAML):
        raise SystemExit(f"{DATA_YAML} not found - run download_dataset.py then prepare_dataset.py first.")

    print(f"Fine-tuning from {BASE_WEIGHTS} on {DATA_YAML}")
    print("Running on CPU (no GPU detected in this environment) - this will be slow; "
          "reduce --epochs or --imgsz if it needs to fit a shorter window.")

    model = YOLO(BASE_WEIGHTS)
    model.train(
        data=DATA_YAML,
        epochs=args.epochs,
        batch=args.batch,
        imgsz=args.imgsz,
        patience=args.patience,
        device="cpu",
        project=RUNS_DIR,
        name="phone_specialist",
    )

    print("\nDone. Best weights at:")
    print(os.path.join(RUNS_DIR, "phone_specialist", "weights", "best.pt"))
    print(
        "\nNext step (not automatic): wire this into object_detection_service.py as a second "
        "YOLO(...) instance/predict call for the phone-only check, keeping the existing "
        "yolov8s.pt model for person counting."
    )
