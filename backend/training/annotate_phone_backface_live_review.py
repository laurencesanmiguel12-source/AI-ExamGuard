"""One-off labeler for datasets/oep-msu/phone_backface_live_review/ - 16 frames captured live
through the actual ExamRoom webcam feed on 2026-07-29 while diagnosing a real detection miss: a
phone held low, back/case facing the camera (the natural orientation when someone is actually
reading their own screen in front of a laptop webcam), which the phone-specialist model scored at
~0.000 confidence in every crop tested, and the pose-model's hand-crop fallback also couldn't
reach because of low wrist-keypoint confidence. See the 2026-07-29 project-status memory entry for
the full diagnostic chain.

Face boxes (class 1) come from the app's real YuNet detector (high-confidence, no guessing needed).
Phone boxes (class 0) for frames with a visible phone come from two sources: the base YOLOv8s COCO
model's own low-confidence "cell phone" (class 67) candidate where it found one, and manual visual
estimates (this script's own PHONE_BOXES dict) for the frames where even the generic COCO detector
found nothing - confirming the whole point of this collection: this composition is hard for
generic phone detectors, not just the fine-tuned specialist.

Like auto_annotate_subject01_review.py, these are DRAFT boxes for LabelImg review, not verified
ground truth - do not merge directly into annotation_batch/ without a human review pass first.

Usage: ../.venv/Scripts/python.exe annotate_phone_backface_live_review.py
"""
import os
import cv2

REVIEW_DIR = os.path.join(os.path.dirname(__file__), "datasets", "oep-msu", "phone_backface_live_review")
YUNET_PATH = os.path.join(os.path.dirname(__file__), "..", "app", "resources", "face_detection_yunet_2023mar.onnx")

PHONE_CLASS = 0
FACE_CLASS = 1

# Manual visual-estimate phone boxes (x1, y1, x2, y2) in pixels, for frames where the base COCO
# model found no candidate at all. Frames not listed here either have no phone (00-02) or use the
# COCO-model draft box captured separately (06, 07, 08, 09, 10, 13, 14).
MANUAL_PHONE_BOXES = {
    "backface_capture_03.jpg": (130, 355, 330, 480),
    "backface_capture_04.jpg": (150, 255, 325, 465),
    "backface_capture_05.jpg": (5, 250, 265, 460),
    "backface_capture_11.jpg": (0, 290, 115, 480),
    "backface_capture_12.jpg": (0, 300, 95, 480),
    "backface_capture_15.jpg": (230, 280, 390, 460),
}

# Larger of the two overlapping candidates where the COCO draft returned nested duplicates.
COCO_DRAFT_PHONE_BOXES = {
    "backface_capture_06.jpg": (30, 309, 155, 475),
    "backface_capture_07.jpg": (32, 309, 165, 480),
    "backface_capture_08.jpg": (5, 304, 157, 480),
    "backface_capture_09.jpg": (17, 302, 156, 480),
    "backface_capture_10.jpg": (17, 292, 154, 480),
    "backface_capture_13.jpg": (1, 302, 126, 480),
    "backface_capture_14.jpg": (257, 267, 393, 448),
}

NO_PHONE_FRAMES = {"backface_capture_00.jpg", "backface_capture_01.jpg", "backface_capture_02.jpg"}


def to_yolo_line(cls, x1, y1, x2, y2, img_w, img_h):
    cx = (x1 + x2) / 2 / img_w
    cy = (y1 + y2) / 2 / img_h
    w = (x2 - x1) / img_w
    h = (y2 - y1) / img_h
    return f"{cls} {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}"


def main():
    detector = cv2.FaceDetectorYN_create(YUNET_PATH, "", (320, 320), 0.6, 0.3, 5000)

    image_files = sorted(f for f in os.listdir(REVIEW_DIR) if f.endswith(".jpg"))
    with open(os.path.join(REVIEW_DIR, "classes.txt"), "w") as f:
        f.write("phone\nface\n")

    written = 0
    for fname in image_files:
        img_path = os.path.join(REVIEW_DIR, fname)
        image = cv2.imread(img_path)
        h, w = image.shape[:2]

        lines = []

        detector.setInputSize((w, h))
        _, faces = detector.detect(image)
        if faces is not None and len(faces) > 0:
            fx, fy, fw, fh = faces[0][:4]
            lines.append(to_yolo_line(FACE_CLASS, fx, fy, fx + fw, fy + fh, w, h))

        if fname in MANUAL_PHONE_BOXES:
            x1, y1, x2, y2 = MANUAL_PHONE_BOXES[fname]
            lines.append(to_yolo_line(PHONE_CLASS, x1, y1, x2, y2, w, h))
        elif fname in COCO_DRAFT_PHONE_BOXES:
            x1, y1, x2, y2 = COCO_DRAFT_PHONE_BOXES[fname]
            lines.append(to_yolo_line(PHONE_CLASS, x1, y1, x2, y2, w, h))
        elif fname not in NO_PHONE_FRAMES:
            print(f"WARNING: {fname} not classified as phone or no-phone - skipping phone label")

        label_path = os.path.join(REVIEW_DIR, os.path.splitext(fname)[0] + ".txt")
        with open(label_path, "w") as f:
            if lines:
                f.write("\n".join(lines) + "\n")
        written += 1

    print(f"{written} label files written to {REVIEW_DIR}")
    print(f"{len(MANUAL_PHONE_BOXES) + len(COCO_DRAFT_PHONE_BOXES)} frames with a phone box, "
          f"{len(NO_PHONE_FRAMES)} verified phone-free negatives")


if __name__ == "__main__":
    main()
