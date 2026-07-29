"""Second live-capture batch for the same back-facing-phone gap as
annotate_phone_backface_live_review.py, this time captured under noticeably different lighting
and with a different phone (blue case vs. the first batch's pink one). Notably, the generic COCO
model detected this phone at 0.8-0.95 confidence in nearly every frame here - much higher than the
first batch - suggesting lighting/phone-color contrast against the background was a real factor in
detectability, not just pose. Still worth adding: more real variety is good, and one frame
(backface_lit2_14.jpg) has no phone in view at all (moved out of frame), a useful hard negative.

Face boxes (class 1) from the real YuNet detector. Phone boxes (class 0) from the base YOLOv8s
COCO model's own draft box, used directly this time since confidence was high across the board
(unlike the first batch, no manual estimates were needed except confirming the two low-confidence
edge cases visually).

Draft labels only - not yet human-reviewed in LabelImg, though the user has said auto draft labels
can be trusted directly this round (see the 2026-07-29 session).

Usage: ../.venv/Scripts/python.exe annotate_phone_backface_live_review2.py
"""
import os
import cv2
from ultralytics import YOLO

REVIEW_DIR = os.path.join(os.path.dirname(__file__), "datasets", "oep-msu", "phone_backface_live_review2")
YUNET_PATH = os.path.join(os.path.dirname(__file__), "..", "app", "resources", "face_detection_yunet_2023mar.onnx")
BASE_MODEL_PATH = os.path.join(os.path.dirname(__file__), "..", "app", "resources", "yolov8s.pt")

PHONE_CLASS = 0
FACE_CLASS = 1
COCO_CELL_PHONE = 67
COCO_CONF_FLOOR = 0.05

# backface_lit2_14.jpg has no phone in view at all - a verified negative, not a missing label.
NO_PHONE_FRAMES = {"backface_lit2_14.jpg"}


def to_yolo_line(cls, x1, y1, x2, y2, img_w, img_h):
    cx = (x1 + x2) / 2 / img_w
    cy = (y1 + y2) / 2 / img_h
    w = (x2 - x1) / img_w
    h = (y2 - y1) / img_h
    return f"{cls} {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}"


def main():
    face_detector = cv2.FaceDetectorYN_create(YUNET_PATH, "", (320, 320), 0.6, 0.3, 5000)
    phone_model = YOLO(BASE_MODEL_PATH)

    image_files = sorted(f for f in os.listdir(REVIEW_DIR) if f.endswith(".jpg"))
    with open(os.path.join(REVIEW_DIR, "classes.txt"), "w") as f:
        f.write("phone\nface\n")

    written = 0
    with_phone = 0
    for fname in image_files:
        img_path = os.path.join(REVIEW_DIR, fname)
        image = cv2.imread(img_path)
        h, w = image.shape[:2]

        lines = []

        face_detector.setInputSize((w, h))
        _, faces = face_detector.detect(image)
        if faces is not None and len(faces) > 0:
            fx, fy, fw, fh = faces[0][:4]
            lines.append(to_yolo_line(FACE_CLASS, fx, fy, fx + fw, fy + fh, w, h))

        if fname not in NO_PHONE_FRAMES:
            result = phone_model.predict(image, verbose=False, conf=COCO_CONF_FLOOR)[0]
            best_box, best_conf = None, 0.0
            for box in result.boxes:
                if int(box.cls[0]) == COCO_CELL_PHONE:
                    conf = float(box.conf[0])
                    if conf > best_conf:
                        best_conf = conf
                        best_box = box.xyxy[0].tolist()
            if best_box is not None:
                lines.append(to_yolo_line(PHONE_CLASS, *best_box, w, h))
                with_phone += 1
            else:
                print(f"WARNING: {fname} expected a phone box but COCO model found none - check manually")

        label_path = os.path.join(REVIEW_DIR, os.path.splitext(fname)[0] + ".txt")
        with open(label_path, "w") as f:
            if lines:
                f.write("\n".join(lines) + "\n")
        written += 1

    print(f"{written} label files written to {REVIEW_DIR}")
    print(f"{with_phone} frames with a phone box, {len(NO_PHONE_FRAMES)} verified phone-free negatives")


if __name__ == "__main__":
    main()
