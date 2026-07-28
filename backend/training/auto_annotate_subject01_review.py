"""One-off variant of auto_annotate_oep.py, scoped ONLY to
datasets/oep-msu/subject01_phonewin_review/ - the 232 newly densely-sampled frames from subject1's
previously under-sampled real phone-use footage (see the 2026-07-28 memory update on extending OEP
coverage). Deliberately does NOT touch datasets/oep-msu/annotation_batch/, since that directory
holds already human-reviewed ground truth and auto_annotate_oep.py overwrites any label file it
finds a candidate box for - rerunning it there would silently clobber prior review work.

Same draft-not-ground-truth caveat applies here too: these boxes are a starting point for LabelImg
review, not something to train on directly.

Usage: ../../.venv/Scripts/python.exe auto_annotate_subject01_review.py
"""
import os

import cv2
from ultralytics import YOLO

REVIEW_DIR = os.path.join(os.path.dirname(__file__), "datasets", "oep-msu", "subject01_phonewin_review")

YOLO_MODEL_PATH = os.path.join(os.path.dirname(__file__), "..", "app", "resources", "yolov8s.pt")
PHONE_SPECIALIST_PATH = os.path.join(
    os.path.dirname(__file__), "..", "app", "resources", "phone_specialist.pt"
)
YUNET_PATH = os.path.join(
    os.path.dirname(__file__), "..", "app", "resources", "face_detection_yunet_2023mar.onnx"
)

COCO_CELL_PHONE_CLASS = 67
PHONE_CONF = 0.15
FACE_SCORE_THRESHOLD = 0.6
IOU_MERGE_THRESHOLD = 0.5

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


def main():
    yolo_model = YOLO(YOLO_MODEL_PATH)
    phone_model = YOLO(PHONE_SPECIALIST_PATH)
    face_detector = cv2.FaceDetectorYN_create(
        YUNET_PATH, "", (320, 320), score_threshold=FACE_SCORE_THRESHOLD, nms_threshold=0.3, top_k=5000
    )

    # classes.txt is required in the same folder for LabelImg's YoloReader to open it without
    # crashing - see the 2026-07-26 LabelImg gotcha in ai_examguard_backend_gotchas memory.
    with open(os.path.join(REVIEW_DIR, "classes.txt"), "w") as f:
        f.write("phone\nface\n")

    image_files = sorted(f for f in os.listdir(REVIEW_DIR) if f.lower().endswith(".jpg"))

    frames_with_phone = 0
    frames_with_face = 0
    frames_with_any = 0
    frames_with_neither = 0

    for i, fname in enumerate(image_files):
        img_path = os.path.join(REVIEW_DIR, fname)
        image = cv2.imread(img_path)
        if image is None:
            continue
        height, width = image.shape[:2]

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

        label_path = os.path.join(REVIEW_DIR, os.path.splitext(fname)[0] + ".txt")
        if lines:
            with open(label_path, "w") as f:
                f.write("\n".join(lines) + "\n")
        else:
            # Empty file so LabelImg shows it as "needs a box drawn from scratch", not skipped.
            open(label_path, "w").close()

        if phone_boxes:
            frames_with_phone += 1
        if face_boxes:
            frames_with_face += 1
        if lines:
            frames_with_any += 1
        else:
            frames_with_neither += 1

        if i % 50 == 0:
            print(f"  {i}/{len(image_files)} processed...")

    print(f"\n{frames_with_any}/{len(image_files)} frames got at least one draft box")
    print(f"  {frames_with_phone} with a phone box, {frames_with_face} with a face box")
    print(f"  {frames_with_neither} frames got NO draft box - these need a box drawn from scratch during review")
    print(f"\nDraft labels written to {REVIEW_DIR} - point LabelImg there. Review every frame; this is a draft, not ground truth.")


if __name__ == "__main__":
    main()
