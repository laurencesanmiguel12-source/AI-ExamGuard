"""Dumps every frame of a video to <out_dir>/frame_NNNN.jpg - used to turn a phone/webcam
recording into a directory analyze_blink_detection_feasibility.py or
analyze_static_image_threshold.py can consume. Checks cv2.imwrite's return value explicitly -
it fails silently (no exception) on a POSIX-style path passed to a native Windows Python, which
cost real time to debug once already.

Usage: python _extract_video_frames.py <video_path> <out_dir>
"""
import os
import sys

import cv2

video_path = sys.argv[1]
out_dir = sys.argv[2]
os.makedirs(out_dir, exist_ok=True)

cap = cv2.VideoCapture(video_path)
i = 0
saved = 0
failed = 0
while True:
    ok, frame = cap.read()
    if not ok:
        break
    out_path = os.path.join(out_dir, f"frame_{i:04d}.jpg")
    if cv2.imwrite(out_path, frame):
        saved += 1
    else:
        failed += 1
    i += 1
cap.release()
print(f"saved: {saved}, failed: {failed}, out_dir: {out_dir}")
