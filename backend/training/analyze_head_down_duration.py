"""Duration-threshold analysis for PROLONGED_HEAD_DOWN, using annotation_batch's 4 densely
timestamped "phonewin" sequences (subject01/06/09/24, ~0.2-0.4s frame spacing, human-labeled
phone-visible boxes). Reconstructs real contiguous "phone visible" episodes per subject purely
from the human labels (independent of any head-pose model) to answer: how long do genuine
phone-use episodes actually last in this dataset? That's the real-world distribution
HEAD_DOWN_DURATION_THRESHOLD_SECONDS should sit against.

Also runs the actual production pitch/fallback pipeline across each sequence and, given a
candidate pitch threshold (passed as an argument, informed by analyze_head_pose_thresholds.py),
reconstructs what a real 5s-interval poller would have seen - lets you sanity-check a duration
threshold against how quickly the *detector* (not just the label) would notice.
"""
import glob
import os
import re
import sys

import cv2

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services.face_service import (  # noqa: E402
    _detect_largest_face,
    _estimate_head_pose,
    _pose_fallback_signals,
    _HEAD_PRESENCE_CONFIDENCE_THRESHOLD,
)

BATCH_DIR = os.path.join(os.path.dirname(__file__), "datasets", "oep-msu", "annotation_batch")


def phone_present(label_path: str) -> bool:
    if not os.path.exists(label_path):
        return False
    with open(label_path) as f:
        classes = [line.split()[0] for line in f if line.strip()]
    return "0" in classes


def load_sequence(subject: str):
    pattern = os.path.join(BATCH_DIR, f"{subject}_phonewin_*.jpg")
    frames = []
    for jpg_path in glob.glob(pattern):
        m = re.search(r"_phonewin_(\d+\.\d+)s\.jpg$", jpg_path)
        if not m:
            continue
        t = float(m.group(1))
        label_path = jpg_path[:-4] + ".txt"
        frames.append((t, jpg_path, phone_present(label_path)))
    frames.sort(key=lambda f: f[0])
    return frames


def label_episodes(frames):
    """Contiguous runs of phone_present=True, purely from human labels. Returns list of
    (start_t, end_t, duration_s, frame_count)."""
    episodes = []
    start = None
    prev_t = None
    for t, _, present in frames:
        if present and start is None:
            start = t
        if not present and start is not None:
            episodes.append((start, prev_t, prev_t - start))
            start = None
        prev_t = t
    if start is not None:
        episodes.append((start, prev_t, prev_t - start))
    return episodes


def main(pitch_threshold: float):
    print(f"Using candidate pitch threshold: {pitch_threshold}\n")

    for subject in ["subject01", "subject06", "subject09", "subject24"]:
        frames = load_sequence(subject)
        if not frames:
            print(f"{subject}: no phonewin frames found, skipping")
            continue

        episodes = label_episodes(frames)
        print(f"=== {subject}: {len(frames)} frames, "
              f"{frames[0][0]:.1f}s-{frames[-1][0]:.1f}s span ===")
        print(f"  Label-based phone-visible episodes ({len(episodes)}):")
        for start, end, dur in episodes:
            print(f"    {start:.1f}s - {end:.1f}s  (duration {dur:.1f}s)")

        # Run the real pipeline across the whole sequence to see how the detector itself
        # would track pitch/fallback through these episodes.
        down_count = 0
        fallback_count = 0
        total_with_signal = 0
        for t, jpg_path, present in frames:
            image = cv2.imread(jpg_path)
            if image is None:
                continue
            detection = _detect_largest_face(image)
            if detection is not None:
                pose = _estimate_head_pose(image, detection)
                if pose is not None:
                    total_with_signal += 1
                    if pose["pitch"] <= pitch_threshold:
                        down_count += 1
            else:
                _, nose_confidence = _pose_fallback_signals(image)
                if nose_confidence >= _HEAD_PRESENCE_CONFIDENCE_THRESHOLD:
                    fallback_count += 1

        print(f"  Detector: {total_with_signal} frames had a numeric pose "
              f"({down_count} below threshold), {fallback_count} frames used the pose fallback "
              f"(YuNet found nothing)")
        print()


if __name__ == "__main__":
    threshold = float(sys.argv[1]) if len(sys.argv) > 1 else -35.0
    main(threshold)
