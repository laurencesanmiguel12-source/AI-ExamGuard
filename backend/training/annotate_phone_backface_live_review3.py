"""Third live-capture batch for the back-facing-phone gap (see
annotate_phone_backface_live_review.py and _review2.py for the first two) - 101 frames captured
in one continuous session, phone held in varied positions/angles/heights throughout.

**Real lesson from this batch, not just a rerun of the same script**: an initial pass trusted the
base COCO model's own draft boxes directly (same approach as batch 2), and only 5/101 frames got a
phone box. Spot-checking a few of the resulting "negatives" found real misses - e.g. frame 040
clearly shows a held phone but both the base COCO model AND the fine-tuned phone_specialist.pt
scored it at ~0.000 confidence. Cross-checking low-confidence candidates from both models also
turned up several FALSE positives (frames 012/025/030/031 had weak specialist-model hits on
background clutter, not the phone). Trusting either model's output blindly here would have both
mislabeled real positives as negatives (actively harmful - poisons exactly the hard cases this
dataset exists to capture) and introduced bogus boxes on frames with no phone at all.

Given both models were unreliable, every frame was reviewed visually (via generated contact-sheet
grids for an efficient overview, then full-resolution single-frame checks at the ambiguous
boundaries) to classify phone-visible vs phone-free, and PHONE_BOXES below are manual pixel
estimates for the confirmed-positive frames (two of them, 034/035, matched the specialist model's
own box closely enough to reuse directly - noted inline). 76 frames are genuine negatives (no
phone in view at any point, confirmed by eye, not assumed from a lack of model confidence).

Face boxes (class 1) are still the real YuNet detector's output - that model had zero disputed
detections during review, unlike the phone detectors.

Usage: ../.venv/Scripts/python.exe annotate_phone_backface_live_review3.py
"""
import os
import cv2

REVIEW_DIR = os.path.join(os.path.dirname(__file__), "datasets", "oep-msu", "phone_backface_live_review3")
YUNET_PATH = os.path.join(os.path.dirname(__file__), "..", "app", "resources", "face_detection_yunet_2023mar.onnx")

PHONE_CLASS = 0
FACE_CLASS = 1

# Manual visual pixel boxes (x1, y1, x2, y2) for every frame confirmed by eye to have a phone
# visible. 034/035 match the phone_specialist.pt model's own box (confidence 0.481/0.575) closely
# enough to reuse rather than re-estimate.
PHONE_BOXES = {
    "backface_100_004.jpg": (65, 445, 215, 480),
    "backface_100_005.jpg": (305, 420, 460, 480),
    "backface_100_006.jpg": (495, 390, 575, 460),
    "backface_100_007.jpg": (505, 395, 580, 465),
    "backface_100_008.jpg": (495, 400, 575, 475),
    "backface_100_009.jpg": (520, 395, 575, 480),
    "backface_100_032.jpg": (435, 325, 585, 480),
    "backface_100_033.jpg": (490, 340, 605, 480),
    "backface_100_034.jpg": (204, 286, 383, 470),
    "backface_100_035.jpg": (212, 290, 387, 471),
    "backface_100_036.jpg": (0, 445, 115, 480),
    "backface_100_037.jpg": (0, 430, 70, 480),
    "backface_100_040.jpg": (75, 345, 260, 480),
    "backface_100_041.jpg": (365, 365, 555, 480),
    "backface_100_042.jpg": (490, 400, 585, 475),
    "backface_100_091.jpg": (190, 415, 340, 480),
    "backface_100_092.jpg": (330, 300, 450, 475),
    "backface_100_093.jpg": (400, 320, 495, 465),
    "backface_100_094.jpg": (460, 370, 560, 480),
    "backface_100_095.jpg": (500, 395, 575, 480),
    "backface_100_096.jpg": (500, 410, 585, 480),
    "backface_100_097.jpg": (490, 415, 590, 480),
    "backface_100_098.jpg": (530, 445, 590, 480),
    "backface_100_099.jpg": (475, 435, 585, 480),
    "backface_100_100.jpg": (480, 440, 590, 480),
}


def to_yolo_line(cls, x1, y1, x2, y2, img_w, img_h):
    cx = (x1 + x2) / 2 / img_w
    cy = (y1 + y2) / 2 / img_h
    w = (x2 - x1) / img_w
    h = (y2 - y1) / img_h
    return f"{cls} {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}"


def main():
    face_detector = cv2.FaceDetectorYN_create(YUNET_PATH, "", (320, 320), 0.6, 0.3, 5000)

    image_files = sorted(f for f in os.listdir(REVIEW_DIR) if f.endswith(".jpg"))
    with open(os.path.join(REVIEW_DIR, "classes.txt"), "w") as f:
        f.write("phone\nface\n")

    written = 0
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

        if fname in PHONE_BOXES:
            x1, y1, x2, y2 = PHONE_BOXES[fname]
            lines.append(to_yolo_line(PHONE_CLASS, x1, y1, x2, y2, w, h))

        label_path = os.path.join(REVIEW_DIR, os.path.splitext(fname)[0] + ".txt")
        with open(label_path, "w") as f:
            if lines:
                f.write("\n".join(lines) + "\n")
        written += 1

    print(f"{written} label files written to {REVIEW_DIR}")
    print(f"{len(PHONE_BOXES)} frames with a phone box, {written - len(PHONE_BOXES)} verified phone-free negatives")


if __name__ == "__main__":
    main()
