"""Draft-labels a personal webcam video for the phone/face training set, using the same
loose-threshold two-model approach as auto_annotate_oep.py (base yolov8s COCO "cell phone" class
+ phone_specialist.pt, YuNet for faces) - draft boxes for a human to correct, not ground truth.

Writes into an ISOLATED new folder, never directly into annotation_batch/ - same discipline as
subject01_phonewin_review/ and every other live-capture batch in this project (see
ai_examguard_backend_gotchas memory: auto_annotate_oep.py clobbering already-reviewed work was a
real near-miss once; new sources always land in their own scoped folder first).

Only frames where at least one of the two phone models fires (at a loose 0.15 confidence) are
kept, padded by a few frames on each side to catch the phone entering/leaving view - the video is
short enough (a couple minutes) to just run detection on every frame rather than pre-scanning at
a lower rate first.

Usage: ../../.venv/Scripts/python.exe prepare_personal_phone_video_review.py <video_path>
"""
import os
import sys

import cv2

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from ultralytics import YOLO  # noqa: E402

OUT_DIR = os.path.join(os.path.dirname(__file__), "datasets", "oep-msu", "personal_phone_video_review")

YOLO_MODEL_PATH = os.path.join(os.path.dirname(__file__), "..", "app", "resources", "yolov8s.pt")
PHONE_SPECIALIST_PATH = os.path.join(
    os.path.dirname(__file__), "..", "app", "resources", "phone_specialist.pt"
)
YUNET_PATH = os.path.join(
    os.path.dirname(__file__), "..", "app", "resources", "face_detection_yunet_2023mar.onnx"
)

COCO_CELL_PHONE_CLASS = 67
PHONE_CONF = 0.15  # loose on purpose, matching auto_annotate_oep.py - see its docstring
FACE_SCORE_THRESHOLD = 0.6
IOU_MERGE_THRESHOLD = 0.5
PAD_FRAMES = 8  # ~0.5s either side at 15fps - catches the phone entering/leaving view

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


def detect(image, yolo_model, phone_model, face_detector):
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

    return phone_boxes, face_boxes


def main(video_path: str):
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(os.path.join(OUT_DIR, "classes.txt"), "w") as f:
        f.write("phone\nface\n")

    yolo_model = YOLO(YOLO_MODEL_PATH)
    phone_model = YOLO(PHONE_SPECIALIST_PATH)
    face_detector = cv2.FaceDetectorYN_create(
        YUNET_PATH, "", (320, 320), score_threshold=FACE_SCORE_THRESHOLD, nms_threshold=0.3, top_k=5000
    )

    cap = cv2.VideoCapture(video_path)
    frames = []
    has_phone = []
    i = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        phone_boxes, face_boxes = detect(frame, yolo_model, phone_model, face_detector)
        frames.append((frame, phone_boxes, face_boxes))
        has_phone.append(bool(phone_boxes))
        if i % 200 == 0:
            print(f"  scanned {i} frames...")
        i += 1
    cap.release()

    print(f"\n{sum(has_phone)}/{len(frames)} frames had a candidate phone box at conf>={PHONE_CONF}")

    keep = [False] * len(frames)
    for idx, flag in enumerate(has_phone):
        if flag:
            for j in range(max(0, idx - PAD_FRAMES), min(len(frames), idx + PAD_FRAMES + 1)):
                keep[j] = True

    saved = 0
    for idx, (frame, phone_boxes, face_boxes) in enumerate(frames):
        if not keep[idx]:
            continue
        height, width = frame.shape[:2]
        lines = [
            to_yolo_line(PHONE_CLASS_OUT, x1, y1, x2, y2, width, height)
            for x1, y1, x2, y2, _ in phone_boxes
        ] + [
            to_yolo_line(FACE_CLASS_OUT, x1, y1, x2, y2, width, height)
            for x1, y1, x2, y2 in face_boxes
        ]
        name = f"personal_video_review_{idx:04d}"
        cv2.imwrite(os.path.join(OUT_DIR, f"{name}.jpg"), frame)
        with open(os.path.join(OUT_DIR, f"{name}.txt"), "w") as f:
            if lines:
                f.write("\n".join(lines) + "\n")
        saved += 1

    print(f"\nSaved {saved} frames (phone-candidate frames + {PAD_FRAMES}-frame padding) to:")
    print(f"  {OUT_DIR}")
    print(
        "\nNext steps (do NOT skip review - see this script's docstring for why):\n"
        "  1. Open this folder in LabelImg, review every frame - correct/delete/add boxes as needed.\n"
        "     Some frames may have an empty .txt (no draft box) despite being in a phone-adjacent\n"
        "     window - those need a box drawn from scratch if a phone is actually visible.\n"
        "  2. Once reviewed, merge into datasets/oep-msu/annotation_batch/ and rerun\n"
        "     prepare_oep_split.py before the next finetune_phone_face.py run."
    )


if __name__ == "__main__":
    main(sys.argv[1])
