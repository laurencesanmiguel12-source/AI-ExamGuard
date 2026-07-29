"""Fine-tune a phone+face specialist on top of the existing yolov8s.pt COCO weights, using the
~22.9k-image reorganized_phone_dataset_yolo set (see backend/training/datasets/phone-face-yolo/
data.yaml - must be downloaded and unpacked locally first, it isn't fetched by this repo).

Class 0 is "phone" and class 1 is "face" in the source labels, matched here by data.yaml's
`names` order, so the resulting model is a drop-in upgrade for app/resources/phone_specialist.pt:
PHONE_SPECIALIST_CLASS = 0 in object_detection_service.py still means "phone". The face class
comes along for free but nothing consumes it yet - face detection in this app currently runs
through the separate YuNet model (app/resources/face_detection_yunet_2023mar.onnx), not YOLO.

Deliberately trains a SEPARATE model rather than overwriting app/resources/yolov8s.pt in place,
for the same reason as finetune_phone.py: this dataset has no "person" class, so training
directly on it rebuilds YOLO's detection head to output only phone/face, which would silently
delete the "person" class the app's MULTIPLE_PEOPLE check depends on. Run this model as a second
inference pass alongside the untouched yolov8s.pt, not as a replacement for it.

This dataset is ~23x the size of the single-class Kaggle set finetune_phone.py trains on, so a
CPU run will take considerably longer per epoch - reduce --epochs or --imgsz if it needs to fit
a shorter window.

Usage: ../../.venv/Scripts/python.exe finetune_phone_face.py [--epochs 30] [--batch 8] [--imgsz 640]
"""
import argparse
import os

import torch
from ultralytics import YOLO

BASE_WEIGHTS = os.path.join(
    os.path.dirname(__file__), "..", "app", "resources", "yolov8s.pt"
)
DATA_YAML = os.path.join(
    os.path.dirname(__file__), "datasets", "phone-face-yolo", "data.yaml"
)
RUNS_DIR = os.path.join(os.path.dirname(__file__), "runs")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--epochs", type=int, default=30)
    parser.add_argument("--batch", type=int, default=8)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--patience", type=int, default=8, help="early-stop patience")
    parser.add_argument("--device", type=str, default=None,
                         help="override auto-detected device, e.g. 'cpu' or '0' for first GPU")
    args = parser.parse_args()

    if not os.path.isfile(DATA_YAML):
        raise SystemExit(
            f"{DATA_YAML} not found. It should point at the unpacked "
            "reorganized_phone_dataset_yolo dataset - edit the paths in that file if you "
            "downloaded it somewhere other than C:\\baidunetdiskdownload."
        )

    if args.device is not None:
        device = args.device
    elif torch.cuda.is_available():
        device = "0"
    else:
        device = "cpu"

    print(f"Fine-tuning from {BASE_WEIGHTS} on {DATA_YAML}")
    if device == "cpu":
        print("Running on CPU (no GPU detected/selected) - this will be slow; "
              "reduce --epochs or --imgsz if it needs to fit a shorter window.")
    else:
        print(f"Running on GPU (device={device}, {torch.cuda.get_device_name(0)})")

    model = YOLO(BASE_WEIGHTS)
    model.train(
        data=DATA_YAML,
        epochs=args.epochs,
        batch=args.batch,
        imgsz=args.imgsz,
        patience=args.patience,
        device=device,
        project=RUNS_DIR,
        name="phone_face_specialist",
    )

    print("\nDone. Best weights at:")
    print(os.path.join(RUNS_DIR, "phone_face_specialist", "weights", "best.pt"))
    print(
        "\nNext step (not automatic): swap this in for app/resources/phone_specialist.pt "
        "(class 0 = phone, matching PHONE_SPECIALIST_CLASS in object_detection_service.py) once "
        "you've compared its val metrics against the current specialist."
    )
