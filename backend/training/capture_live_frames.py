"""Captures a burst of raw webcam frames at a fixed interval, for the live smoke-test gate that
analyze_landmark_geometry_liveness.py's docstring requires before any production decision (real
photo/real tremor, not the synthetic warpAffine perturbation the offline result used). Opens the
camera directly (cv2.VideoCapture) rather than going through the app's /face-check endpoint - same
webcam feed, simpler for a one-off capture burst with no exam session needed.

Usage: python capture_live_frames.py <output_dir> <label> <num_frames> <interval_seconds>
Saves <output_dir>/<label>_00.jpg, _01.jpg, ... - a 3s countdown before the first capture gives
the subject a moment to get in position.
"""
import os
import sys
import time

import cv2


def main(output_dir: str, label: str, num_frames: int, interval_seconds: float):
    os.makedirs(output_dir, exist_ok=True)

    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    if not cap.isOpened():
        print("Could not open webcam.")
        return

    print(f"Starting in 3s - get in position for '{label}'...")
    time.sleep(3)

    for i in range(num_frames):
        ok, frame = cap.read()
        if not ok:
            print(f"  frame {i}: capture failed, skipping")
            continue
        path = os.path.join(output_dir, f"{label}_{i:02d}.jpg")
        cv2.imwrite(path, frame)
        print(f"  saved {path}")
        if i < num_frames - 1:
            time.sleep(interval_seconds)

    cap.release()
    print("Done.")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], int(sys.argv[3]), float(sys.argv[4]))
