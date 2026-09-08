"""Draft-annotate the new_dataset webcam videos (6 people / ~5 rooms, extracted to
datasets/new_video/frames/ at ~1fps) for phone + face boxes, and record the real production
head-pose pitch per frame for head-down threshold re-validation.

Same discipline as auto_annotate_oep.py: loose two-model phone pass (base COCO "cell phone" +
phone_specialist.pt) unioned, YuNet faces, then the SAME geometric FP filter production already
uses (drop phone boxes whose IoU with a same-frame face box >= 0.45 - the validated
face-anchored-FP suppressor, see ai_examguard_phone_detection_personal_video_labeling). Output is
a DRAFT for review, not ground truth - see auto_annotate_oep.py's docstring for why training on an
un-reviewed auto-label just teaches the next model this model's blind spots.

Writes:
  datasets/new_video/frames/<frame>.txt      YOLO labels (0=phone, 1=face)
  datasets/new_video/head_pose.csv           per-frame pitch/yaw + fallback, real pipeline
  datasets/new_video/annotate_stats.json     per-video counts

Usage: ../.venv/Scripts/python.exe annotate_new_video.py
"""
import csv, glob, json, os, sys
from collections import defaultdict

import cv2
import numpy as np
from ultralytics import YOLO

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import app.services.face_service as fs  # noqa: E402

HERE = os.path.dirname(__file__)
FRAMES = os.path.join(HERE, "datasets", "new_video", "frames")
OUT = os.path.join(HERE, "datasets", "new_video")
RES = os.path.join(HERE, "..", "app", "resources")

PHONE_SPECIALIST_PATH = os.path.join(RES, "phone_specialist.pt")
BASE_YOLO_PATH = os.path.join(RES, "yolov8s.pt")
YUNET_PATH = os.path.join(RES, "face_detection_yunet_2023mar.onnx")

COCO_CELL_PHONE = 67
SPEC_PHONE_CLASS, SPEC_FACE_CLASS = 0, 1
PHONE_CONF = 0.15          # loose on purpose (draft-then-review)
FACE_SCORE = 0.6           # loose vs prod 0.9 - draft
IOU_MERGE = 0.5            # dedupe the two phone models
FACE_ANCHOR_IOU = 0.45     # production's validated face-shaped-FP suppressor

PHONE_OUT, FACE_OUT = 0, 1


def iou(a, b):
    ix1, iy1 = max(a[0], b[0]), max(a[1], b[1])
    ix2, iy2 = min(a[2], b[2]), min(a[3], b[3])
    if ix2 <= ix1 or iy2 <= iy1:
        return 0.0
    inter = (ix2 - ix1) * (iy2 - iy1)
    return inter / ((a[2]-a[0])*(a[3]-a[1]) + (b[2]-b[0])*(b[3]-b[1]) - inter)


def merge(cands):
    cands = sorted(cands, key=lambda c: -c[4])
    kept = []
    for c in cands:
        if all(iou(c[:4], k[:4]) < IOU_MERGE for k in kept):
            kept.append(c)
    return kept


def yolo_line(cls, x1, y1, x2, y2, w, h):
    return (f"{cls} {((x1+x2)/2)/w:.6f} {((y1+y2)/2)/h:.6f} "
            f"{(x2-x1)/w:.6f} {(y2-y1)/h:.6f}")


def main():
    spec = YOLO(PHONE_SPECIALIST_PATH)
    base = YOLO(BASE_YOLO_PATH)
    yunet = cv2.FaceDetectorYN_create(YUNET_PATH, "", (320, 320),
                                      score_threshold=FACE_SCORE, nms_threshold=0.3, top_k=5000)

    files = sorted(glob.glob(os.path.join(FRAMES, "*.jpg")))
    print(f"{len(files)} frames")
    pose_rows = []
    stats = defaultdict(lambda: {"n": 0, "phone": 0, "face": 0, "suppressed": 0,
                                 "pitch_down": 0, "no_face": 0})

    for i, fp in enumerate(files):
        img = cv2.imread(fp)
        if img is None:
            continue
        h, w = img.shape[:2]
        video = os.path.basename(fp).rsplit("_f", 1)[0]
        st = stats[video]
        st["n"] += 1

        cands = []
        br = base.predict(img, verbose=False, conf=PHONE_CONF)[0]
        for b in br.boxes:
            if int(b.cls[0]) == COCO_CELL_PHONE:
                x1, y1, x2, y2 = b.xyxy[0].tolist()
                cands.append((x1, y1, x2, y2, float(b.conf[0])))
        sr = spec.predict(img, verbose=False, conf=PHONE_CONF)[0]
        face_boxes_spec = [tuple(map(float, b.xyxy[0])) for b in sr.boxes
                           if int(b.cls[0]) == SPEC_FACE_CLASS]
        for b in sr.boxes:
            if int(b.cls[0]) == SPEC_PHONE_CLASS:
                x1, y1, x2, y2 = b.xyxy[0].tolist()
                cands.append((x1, y1, x2, y2, float(b.conf[0])))
        phones = merge(cands)

        yunet.setInputSize((w, h))
        _, faces = yunet.detect(img)
        face_boxes = []
        if faces is not None:
            for f in faces:
                x, y, fw, fh = f[:4]
                face_boxes.append((max(0.0, x), max(0.0, y),
                                   min(float(w), x + fw), min(float(h), y + fh)))
        # union YuNet + specialist's own face class for the suppression test (more complete)
        all_faces = face_boxes + face_boxes_spec

        kept_phones = []
        for p in phones:
            if any(iou(p[:4], fb) >= FACE_ANCHOR_IOU for fb in all_faces):
                st["suppressed"] += 1
            else:
                kept_phones.append(p)

        lines = [yolo_line(PHONE_OUT, *p[:4], w, h) for p in kept_phones]
        lines += [yolo_line(FACE_OUT, *fb, w, h) for fb in face_boxes]
        with open(fp[:-4] + ".txt", "w") as f:
            f.write("\n".join(lines) + ("\n" if lines else ""))
        if kept_phones:
            st["phone"] += 1
        if face_boxes:
            st["face"] += 1

        det = fs._detect_largest_face(img)
        pose = fs._estimate_head_pose(img, det) if det is not None else None
        fallback = None
        if det is None:
            st["no_face"] += 1
            _, nose_conf = fs._pose_fallback_signals(img)
            fallback = nose_conf >= fs._HEAD_PRESENCE_CONFIDENCE_THRESHOLD
        pitch = pose["pitch"] if pose else ""
        if pose and pose["pitch"] <= fs.HEAD_DOWN_PITCH_THRESHOLD_DEGREES:
            st["pitch_down"] += 1
        pose_rows.append({
            "file": os.path.basename(fp), "video": video,
            "phone_boxes": len(kept_phones), "face_boxes": len(face_boxes),
            "yunet_face": det is not None,
            "pitch": pitch, "yaw": pose["yaw"] if pose else "",
            "roll": pose["roll"] if pose else "",
            "fallback_head_present": "" if fallback is None else fallback,
        })

        if (i + 1) % 200 == 0:
            print(f"  {i+1}/{len(files)}")

    with open(os.path.join(OUT, "head_pose.csv"), "w", newline="") as f:
        wtr = csv.DictWriter(f, fieldnames=list(pose_rows[0].keys()))
        wtr.writeheader()
        wtr.writerows(pose_rows)
    with open(os.path.join(OUT, "annotate_stats.json"), "w") as f:
        json.dump(stats, f, indent=1)

    print("\n=== per-video ===")
    for v, s in sorted(stats.items()):
        print(f"{v[:40]:40s} n={s['n']:4d} phone_frames={s['phone']:4d} "
              f"face_frames={s['face']:4d} FP_suppressed={s['suppressed']:4d} "
              f"pitch<=-35={s['pitch_down']:4d} no_face={s['no_face']:4d}")
    tot_phone = sum(s["phone"] for s in stats.values())
    tot = sum(s["n"] for s in stats.values())
    print(f"\n{tot_phone}/{tot} frames got a draft phone box. "
          f"Review datasets/new_video/frames/ before training on it.")


if __name__ == "__main__":
    main()
