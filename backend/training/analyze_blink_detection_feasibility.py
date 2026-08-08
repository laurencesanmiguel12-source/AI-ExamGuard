"""Feasibility check for blink-based liveness detection, BEFORE building any production
mechanism - the static-image frame-diff check just showed a real ceiling against hand-held
photos (see face_service.py's STATIC_IMAGE_DIFF_THRESHOLD comment), and blink detection is the
proposed alternative signal, since no photo (hand-held or rigid) can blink.

The catch: YuNet only gives a single (x, y) point per eye, not the multi-point eyelid contour a
classic Eye-Aspect-Ratio blink detector needs (dlib's 68-point model, e.g.). This script checks
whether a cheap proxy - Laplacian variance (texture/sharpness) in a small crop centered on each
eye point - actually dips during a real blink, before any of that gets wired into face_service.py.
Rationale: an open eye has real texture (iris/pupil/sclera contrast, eyelashes); a closed eye is
mostly smooth skin/eyelid - lower Laplacian variance. This is speculative until seen on real data.

Usage: python analyze_blink_detection_feasibility.py <frames_dir>
Frames should be a real sequence (ideally ~2fps or faster) spanning at least one deliberate blink.

RESULT (2026-08-08): NOT VIABLE as implemented. Tested against three independent real datasets -
a live capture (this session, claude-in-chrome driving the real webcam), the OEP-MSU dataset's
dense 5fps subject01 sequence, and a personal ~2-minute/15fps webcam video - using a local-minima
detector to flag candidate dips (both eyes' scores dropping together relative to a rolling local
baseline). Every single candidate across all three datasets, checked by eye against the actual
face crop, turned out to be a head-pose/motion artifact (head tilted down, turning, or motion
blur) - not a genuine isolated blink with the head otherwise stable. Not one clean example of
"eyes open -> closed -> open again, head stable" was found. Root cause: YuNet's single eye-point
landmark plus a small fixed-ratio crop is not robust to the small natural head movements that
happen constantly during normal computer use (reading, glancing down, adjusting posture) - those
movements dominate the signal far more than eyelid closure does. See
analyze_static_image_threshold.py's STATIC_IMAGE_DIFF_THRESHOLD finding for the same-shaped
conclusion from the other liveness approach tried the same day. Reliable blink detection would
need a real eyelid-contour landmark model (e.g. MediaPipe FaceMesh, dlib 68-point) - a genuine new
dependency this project doesn't currently have, not a fix to this script's technique.
"""
import glob
import os
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services.face_service import _detect_largest_face  # noqa: E402


def _eye_openness(image_gray, eye_x, eye_y, half_size):
    x0, x1 = max(0, int(eye_x - half_size)), int(eye_x + half_size)
    y0, y1 = max(0, int(eye_y - half_size)), int(eye_y + half_size)
    crop = image_gray[y0:y1, x0:x1]
    if crop.size == 0:
        return None
    return cv2.Laplacian(crop, cv2.CV_64F).var()


def main(frames_dir: str):
    paths = sorted(glob.glob(os.path.join(frames_dir, "*.jpg")))
    print(f"Found {len(paths)} frames in {frames_dir}\n")
    print(f"{'frame':<20} {'right_eye':>10} {'left_eye':>10} {'min':>8}")

    results = []
    for path in paths:
        image = cv2.imread(path)
        if image is None:
            continue
        detection = _detect_largest_face(image)
        if detection is None:
            print(f"{os.path.basename(path):<20} no face detected")
            continue

        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        right_eye_x, right_eye_y = detection[4], detection[5]
        left_eye_x, left_eye_y = detection[6], detection[7]

        # Eye crop half-size scaled to inter-eye distance so it's roughly scale-invariant to
        # camera distance, same principle as HAND_CROP_SIZE/FACE_SIZE elsewhere in this codebase.
        inter_eye_dist = float(np.hypot(left_eye_x - right_eye_x, left_eye_y - right_eye_y))
        half_size = inter_eye_dist * 0.22

        right_score = _eye_openness(gray, right_eye_x, right_eye_y, half_size)
        left_score = _eye_openness(gray, left_eye_x, left_eye_y, half_size)
        if right_score is None or left_score is None:
            print(f"{os.path.basename(path):<20} eye crop out of bounds")
            continue

        min_score = min(right_score, left_score)
        results.append((os.path.basename(path), right_score, left_score, min_score))
        print(f"{os.path.basename(path):<20} {right_score:>10.1f} {left_score:>10.1f} {min_score:>8.1f}")

    if len(results) < 2:
        print("\nNot enough usable frames to say anything.")
        return

    mins = [r[3] for r in results]
    print(f"\nmin-eye-score across sequence: min={min(mins):.1f}, median={sorted(mins)[len(mins)//2]:.1f}, max={max(mins):.1f}")
    print(
        "\nLook for a frame where both eyes' scores drop sharply relative to their neighbors - "
        "that's a candidate blink. If nothing dips clearly below the surrounding baseline, this "
        "specific proxy metric doesn't work at this resolution/distance and a different one (or "
        "a different technique entirely) is needed before building anything on top of it."
    )


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else ".")
