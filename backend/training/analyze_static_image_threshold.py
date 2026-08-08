"""One-off analysis: measures the real consecutive-poll frame-to-frame difference for a genuine
still-sitting sequence, to check whether STATIC_IMAGE_DIFF_THRESHOLD/STATIC_IMAGE_STREAK_THRESHOLD
(face_service.py, both explicitly documented as unvalidated placeholders) would false-positive on
normal sitting-still behavior.

Input: a directory of JPEG frames captured live via the browser (see the 2026-08-08 session that
built this - claude-in-chrome captured 10 real frames of a real enrolled student sitting normally,
~4s apart, via the exact same webcam feed the app itself polls). Runs the real production
detect+crop pipeline (face_service._detect_largest_face/_crop_from_detection) on each frame, then
reports the same mean-absolute-pixel-difference metric _check_static_image computes internally,
for every consecutive pair.

Usage: python analyze_static_image_threshold.py <frames_dir>
"""
import glob
import os
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services.face_service import (  # noqa: E402
    STATIC_IMAGE_DIFF_THRESHOLD,
    STATIC_IMAGE_STREAK_THRESHOLD,
    _crop_from_detection,
    _detect_largest_face,
)


def main(frames_dir: str):
    paths = sorted(glob.glob(os.path.join(frames_dir, "*.jpg")))
    print(f"Found {len(paths)} frames in {frames_dir}")

    crops = []
    for path in paths:
        image = cv2.imread(path)
        if image is None:
            print(f"  {os.path.basename(path)}: couldn't decode, skipping")
            continue
        detection = _detect_largest_face(image)
        if detection is None:
            print(f"  {os.path.basename(path)}: no face detected, skipping")
            continue
        crops.append((os.path.basename(path), _crop_from_detection(image, detection)))

    print(f"\n{len(crops)}/{len(paths)} frames had a detectable face.\n")

    diffs = []
    streak = 0
    fired_at = []
    for i in range(1, len(crops)):
        name_a, crop_a = crops[i - 1]
        name_b, crop_b = crops[i]
        diff = float(np.mean(np.abs(crop_b.astype(np.int16) - crop_a.astype(np.int16))))
        diffs.append(diff)

        if diff < STATIC_IMAGE_DIFF_THRESHOLD:
            streak += 1
        else:
            streak = 0

        flag = " <- would flag STATIC_IMAGE_SUSPECTED here" if streak >= STATIC_IMAGE_STREAK_THRESHOLD else ""
        if flag:
            fired_at.append(name_b)
        print(f"  {name_a} -> {name_b}: diff={diff:.2f}  streak={streak}{flag}")

    diffs.sort()
    n = len(diffs)
    print(f"\nConsecutive-pair diff distribution: n={n}, min={diffs[0]:.2f}, "
          f"median={diffs[n // 2]:.2f}, max={diffs[-1]:.2f}")
    print(f"Current STATIC_IMAGE_DIFF_THRESHOLD={STATIC_IMAGE_DIFF_THRESHOLD}, "
          f"STATIC_IMAGE_STREAK_THRESHOLD={STATIC_IMAGE_STREAK_THRESHOLD}")

    if fired_at:
        print(f"\n*** FALSE POSITIVE RISK: would have fired STATIC_IMAGE_SUSPECTED on real, "
              f"genuine still-sitting behavior at: {fired_at} ***")
    else:
        print("\nNo false-positive fire on this real still-sitting sequence at current settings.")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else ".")
