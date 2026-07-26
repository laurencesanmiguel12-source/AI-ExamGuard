"""Generate DRAFT phone/face bounding boxes for backend/training/datasets/oep-msu/annotation_batch/
using the app's existing detectors (YuNet for faces, phone_specialist.pt + base yolov8s's COCO
"cell phone" class for phones), so LabelImg opens with boxes already drawn to correct rather than
an empty canvas to draw on from scratch.

IMPORTANT - this is a starting point, not ground truth. It must be reviewed and corrected by hand,
for two reasons:
1. Any auto-labeler makes mistakes (missed detections, false positives, imprecise box edges).
2. More fundamentally: the whole reason this data collection effort exists is that the CURRENT
   phone_specialist.pt misses phones in some conditions (that's why a bigger/better dataset is
   being built). Training the NEXT model on THIS model's own uncorrected guesses would just teach
   it to reproduce its existing blind spots instead of fixing them. Auto-labels are only useful
   here as a labor-saving draft for a human to correct - not as a substitute for that correction.

Thresholds are deliberately looser than object_detection_service.py's production settings (which
are tuned to avoid false alarms) - for a draft-then-review workflow, a missed detection costs more
(drawing a box from scratch) than a false positive (one click to delete), so this errs toward
higher recall / lower precision on purpose.

Usage: ../../.venv/Scripts/python.exe auto_annotate_oep.py
"""
import csv
import os

import cv2
import numpy as np
from ultralytics import YOLO

BATCH_DIR = os.path.join(os.path.dirname(__file__), "datasets", "oep-msu", "annotation_batch")
MANIFEST = os.path.join(os.path.dirname(__file__), "datasets", "oep-msu", "frame_priority.csv")

YOLO_MODEL_PATH = os.path.join(os.path.dirname(__file__), "..", "app", "resources", "yolov8s.pt")
PHONE_SPECIALIST_PATH = os.path.join(
    os.path.dirname(__file__), "..", "app", "resources", "phone_specialist.pt"
)
YUNET_PATH = os.path.join(
    os.path.dirname(__file__), "..", "app", "resources", "face_detection_yunet_2023mar.onnx"
)

COCO_CELL_PHONE_CLASS = 67
PHONE_CONF = 0.15  # loose on purpose - see docstring
FACE_SCORE_THRESHOLD = 0.6  # loose on purpose (production uses 0.9) - see docstring
IOU_MERGE_THRESHOLD = 0.5  # dedupe overlapping phone boxes from the two phone models

PHONE_CLASS_OUT = 0
FACE_CLASS_OUT = 1


def iou(a, b):
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    ix1, iy1 = max(ax1, bx1), max(ay1, by1)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    if ix2 <= ix1 or iy2 <= iy1:
        return 0.0
    inter = (ix2 - ix1) * (iy2 - iy1)
    area_a = (ax2 - ax1) * (ay2 - ay1)
    area_b = (bx2 - bx1) * (by2 - by1)
    return inter / (area_a + area_b - inter)


def merge_phone_boxes(candidates):
    # candidates: list of (x1, y1, x2, y2, conf). Keep highest-conf box in each overlapping cluster.
    candidates = sorted(candidates, key=lambda c: -c[4])
    kept = []
    for cand in candidates:
        if all(iou(cand[:4], k[:4]) < IOU_MERGE_THRESHOLD for k in kept):
            kept.append(cand)
    return kept


def to_yolo_line(cls_id, x1, y1, x2, y2, width, height):
    cx = ((x1 + x2) / 2) / width
    cy = ((y1 + y2) / 2) / height
    w = (x2 - x1) / width
    h = (y2 - y1) / height
    return f"{cls_id} {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}"


def load_known_phone_frames():
    with open(MANIFEST) as f:
        return {
            os.path.basename(row["frame_path"])
            for row in csv.DictReader(f)
            if row["priority"] == "phone"
        }


def main():
    known_phone_frames = load_known_phone_frames()
    yolo_model = YOLO(YOLO_MODEL_PATH)
    phone_model = YOLO(PHONE_SPECIALIST_PATH)
    face_detector = cv2.FaceDetectorYN_create(
        YUNET_PATH, "", (320, 320), score_threshold=FACE_SCORE_THRESHOLD, nms_threshold=0.3, top_k=5000
    )

    image_files = sorted(f for f in os.listdir(BATCH_DIR) if f.lower().endswith(".jpg"))

    frames_with_phone = 0
    frames_with_face = 0
    frames_with_any = 0
    known_phone_frames_hit = 0
    known_phone_frames_total = 0

    for i, fname in enumerate(image_files):
        img_path = os.path.join(BATCH_DIR, fname)
        image = cv2.imread(img_path)
        if image is None:
            continue
        height, width = image.shape[:2]

        # Phone candidates: base yolov8s COCO class 67, plus the fine-tuned specialist.
        phone_candidates = []
        yolo_results = yolo_model.predict(image, verbose=False, conf=PHONE_CONF)[0]
        if yolo_results.boxes is not None:
            for box in yolo_results.boxes:
                if int(box.cls[0]) == COCO_CELL_PHONE_CLASS:
                    x1, y1, x2, y2 = box.xyxy[0].tolist()
                    phone_candidates.append((x1, y1, x2, y2, float(box.conf[0])))
        specialist_results = phone_model.predict(image, verbose=False, conf=PHONE_CONF)[0]
        if specialist_results.boxes is not None:
            for box in specialist_results.boxes:
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                phone_candidates.append((x1, y1, x2, y2, float(box.conf[0])))
        phone_boxes = merge_phone_boxes(phone_candidates)

        # Face candidates via YuNet.
        face_detector.setInputSize((width, height))
        _, faces = face_detector.detect(image)
        face_boxes = []
        if faces is not None:
            for f in faces:
                x, y, w, h = f[:4]
                face_boxes.append((max(0, x), max(0, y), min(width, x + w), min(height, y + h)))

        lines = [
            to_yolo_line(PHONE_CLASS_OUT, x1, y1, x2, y2, width, height)
            for x1, y1, x2, y2, _ in phone_boxes
        ] + [
            to_yolo_line(FACE_CLASS_OUT, x1, y1, x2, y2, width, height)
            for x1, y1, x2, y2 in face_boxes
        ]

        if lines:
            label_path = os.path.join(BATCH_DIR, os.path.splitext(fname)[0] + ".txt")
            with open(label_path, "w") as f:
                f.write("\n".join(lines) + "\n")

        if phone_boxes:
            frames_with_phone += 1
        if face_boxes:
            frames_with_face += 1
        if lines:
            frames_with_any += 1

        if fname in known_phone_frames:
            known_phone_frames_total += 1
            if phone_boxes:
                known_phone_frames_hit += 1

        if i % 200 == 0:
            print(f"  {i}/{len(image_files)} processed...")

    print(f"\n{frames_with_any}/{len(image_files)} frames got at least one draft box")
    print(f"  {frames_with_phone} with a phone box, {frames_with_face} with a face box")
    if known_phone_frames_total:
        recall_pct = 100 * known_phone_frames_hit / known_phone_frames_total
        print(
            f"\nOn the {known_phone_frames_total} frames we KNOW contain a phone (from gt.txt "
            f"timestamps), the auto-labeler drew a candidate phone box on {known_phone_frames_hit} "
            f"({recall_pct:.0f}%) - the other {known_phone_frames_total - known_phone_frames_hit} "
            "need a box drawn from scratch during review, not just corrected."
        )
    print(
        "\nDraft labels written directly into annotation_batch/ - reopen LabelImg (already pointed "
        "there) and boxes should now show up pre-drawn. Review every frame; this is a draft, not "
        "ground truth (see docstring)."
    )


if __name__ == "__main__":
    main()
