"""Saves the real production face-detection crop (not just a raw frame) for specific frame
indices in a directory of extracted video frames - for visually spot-checking a candidate flagged
by _find_blink_candidates.py or any other index-based investigation.

Usage: python _extract_face_crops.py <frames_dir> <out_dir> <index> [index...]
"""
import os
import sys

import cv2

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from app.services.face_service import _detect_largest_face  # noqa: E402

frames_dir = sys.argv[1]
out_dir = sys.argv[2]
indices = [int(x) for x in sys.argv[3:]]
os.makedirs(out_dir, exist_ok=True)

for i in indices:
    name = f"frame_{i:04d}.jpg"
    path = os.path.join(frames_dir, name)
    image = cv2.imread(path)
    if image is None:
        print(name, "couldn't read image")
        continue
    detection = _detect_largest_face(image)
    if detection is None:
        print(name, "no face detected")
        continue
    x, y, w, h = detection[:4].astype(int)
    face_crop = image[max(0, y):y + h, max(0, x):x + w]
    out_path = os.path.join(out_dir, f"face_{i:04d}.png")
    cv2.imwrite(out_path, face_crop)
    print(name, "saved ->", out_path)
