"""Fourth live-capture batch for the back-facing-phone gap (see annotate_phone_backface_live_review.py,
_review2.py, and _review3.py for the first three) - 100 frames captured in one continuous session
with a different phone case and different room lighting than any prior batch, phone held in varied
positions/heights/angles throughout, with several genuine phone-free stretches mixed in.

**Same lesson as batch 3, re-confirmed**: the base COCO model (yolov8s.pt) and the fine-tuned
phone_specialist.pt were both probed for draft boxes (low-confidence sweep, plus the pose-guided
wrist-crop fallback) before doing any manual work. The specialist model was unusable here - it
scored a HIGH-confidence (0.5-0.85) "phone" box on the subject's own face in nearly every single
frame, including frames with no phone anywhere in view. The base COCO model was more trustworthy
but low-recall: it only produced a plausible, correctly-located box on about a third of the frames
confirmed by eye to have a visible phone, and was silent (or near-zero confidence) on the rest -
particularly the small-in-frame / partially-cropped poses.

Every frame was reviewed visually: an initial contact-sheet overview pass, then a coordinate-gridded
bottom-of-frame crop pass for a first box estimate, then a full-resolution single-frame check for
every frame either confirmed or suspected positive (the gridded-crop estimates alone proved
unreliable for exact coordinates - cross-checking against the few frames where COCO also had a
confident hit showed the crop-based reads were systematically off, so the full-resolution image was
treated as ground truth for the final box in every case). PHONE_BOXES below are the resulting manual
pixel boxes; a handful (003/005/014/015/016/017/018/019/021/022/023/036/080/083/085/087/097) matched
or closely tracked the COCO model's own box and reused/blended it rather than re-estimating from
scratch.

**Notable pattern found in this batch**: several frames (007/010/011) show the subject's visible
hand touching their face/hair with no phone in it, while a second, mostly-out-of-frame hand still
holds the phone low at the very edge of the shot (a thin sliver, easy to miss). Caught by checking
the full frame rather than trusting the "empty-looking" hand-to-face pose as automatically
phone-free - one more reason not to assume presence/absence from a quick glance.

Face boxes (class 1) are the real YuNet detector's output, same as every prior batch - unlike the
phone detectors it had zero disputed detections during review.

Usage: ../.venv/Scripts/python.exe annotate_phone_backface_live_review4.py
"""
import os
import cv2

REVIEW_DIR = os.path.join(os.path.dirname(__file__), "datasets", "oep-msu", "phone_backface_live_review4")
YUNET_PATH = os.path.join(os.path.dirname(__file__), "..", "app", "resources", "face_detection_yunet_2023mar.onnx")

PHONE_CLASS = 0
FACE_CLASS = 1

# Manual pixel boxes (x1, y1, x2, y2) for every frame confirmed by eye (full-resolution check) to
# have a phone visible, however small/partial.
PHONE_BOXES = {
    "backface4_001.jpg": (400, 380, 535, 480),
    "backface4_002.jpg": (390, 365, 520, 480),
    "backface4_003.jpg": (400, 381, 544, 479),
    "backface4_004.jpg": (440, 395, 560, 480),
    "backface4_005.jpg": (391, 362, 523, 469),
    "backface4_006.jpg": (400, 390, 500, 480),
    "backface4_007.jpg": (455, 450, 565, 480),
    "backface4_009.jpg": (435, 415, 545, 480),
    "backface4_010.jpg": (410, 390, 520, 480),
    "backface4_011.jpg": (485, 448, 545, 480),
    "backface4_012.jpg": (480, 410, 575, 480),
    "backface4_013.jpg": (30, 440, 195, 480),
    "backface4_014.jpg": (222, 421, 355, 480),
    "backface4_015.jpg": (238, 402, 383, 480),
    "backface4_016.jpg": (238, 399, 384, 480),
    "backface4_017.jpg": (221, 395, 352, 480),
    "backface4_018.jpg": (220, 394, 352, 480),
    "backface4_019.jpg": (221, 399, 355, 480),
    "backface4_020.jpg": (390, 270, 515, 470),
    "backface4_021.jpg": (424, 305, 531, 476),
    "backface4_022.jpg": (1, 284, 179, 480),
    "backface4_023.jpg": (0, 259, 127, 468),
    "backface4_025.jpg": (0, 140, 45, 335),
    "backface4_034.jpg": (355, 405, 495, 480),
    "backface4_035.jpg": (440, 465, 490, 480),
    "backface4_036.jpg": (385, 383, 512, 480),
    "backface4_037.jpg": (415, 390, 505, 480),
    "backface4_038.jpg": (420, 380, 500, 480),
    "backface4_039.jpg": (406, 383, 495, 470),
    "backface4_040.jpg": (460, 360, 535, 480),
    "backface4_041.jpg": (400, 355, 515, 480),
    "backface4_061.jpg": (400, 265, 490, 390),
    "backface4_080.jpg": (202, 309, 343, 460),
    "backface4_081.jpg": (400, 390, 515, 480),
    "backface4_082.jpg": (350, 410, 478, 480),
    "backface4_083.jpg": (56, 420, 201, 480),
    "backface4_085.jpg": (255, 400, 403, 480),
    "backface4_086.jpg": (445, 415, 600, 480),
    "backface4_087.jpg": (161, 457, 317, 480),
    "backface4_091.jpg": (450, 415, 535, 480),
    "backface4_094.jpg": (0, 460, 45, 480),
    "backface4_095.jpg": (390, 395, 505, 480),
    "backface4_096.jpg": (410, 415, 520, 480),
    "backface4_097.jpg": (30, 449, 177, 480),
    "backface4_099.jpg": (285, 445, 420, 480),
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
