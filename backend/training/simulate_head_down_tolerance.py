"""Follow-up to simulate_head_down_system.py: that script found the production _track_head_down
state machine NEVER fires across all 4 real timestamped sequences, even during genuine 28-43s
sustained phone-use episodes - because a single noisy poll where pitch happens to read above
threshold resets the ENTIRE streak to zero, discarding all accumulated progress. This script
tests whether tolerating a small number of consecutive "miss" polls before resetting (a grace
period) fixes real-episode detection without opening the door to false positives on
phone-absent stretches. Does NOT modify face_service.py - this is a standalone experiment to
decide whether that change is worth making.
"""
import glob
import os
import re
import sys

import cv2

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import app.services.face_service as face_service  # noqa: E402

BATCH_DIR = os.path.join(os.path.dirname(__file__), "datasets", "oep-msu", "annotation_batch")
POLL_INTERVAL_S = 5.0


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


def resample_at_poll_interval(frames, interval_s=POLL_INTERVAL_S):
    if not frames:
        return []
    start, end = frames[0][0], frames[-1][0]
    picks = []
    t = start
    while t <= end:
        picks.append(min(frames, key=lambda f: abs(f[0] - t)))
        t += interval_s
    return picks


def get_is_down_series(subject: str, pitch_threshold: float):
    """Runs the real detector once per subject and caches (t, present, is_down) - reused across
    every miss_tolerance value we sweep, so we don't re-run YuNet/solvePnP/pose-model per value."""
    frames = load_sequence(subject)
    polls = resample_at_poll_interval(frames)
    face_service.HEAD_DOWN_PITCH_THRESHOLD_DEGREES = pitch_threshold

    series = []
    for t, jpg_path, present in polls:
        image = cv2.imread(jpg_path)
        detection = face_service._detect_largest_face(image)
        pose = face_service._estimate_head_pose(image, detection) if detection is not None else None
        fallback = False
        if detection is None:
            _, nose_confidence = face_service._pose_fallback_signals(image)
            fallback = nose_confidence >= face_service._HEAD_PRESENCE_CONFIDENCE_THRESHOLD
        is_down = face_service._is_head_down(pose, fallback)
        series.append((t, present, is_down))
    return series


def simulate_with_tolerance(series, duration_threshold: float, miss_tolerance: int):
    """miss_tolerance=0 matches current production behavior exactly (any single miss resets).
    miss_tolerance=N means up to N consecutive non-down polls are forgiven - the streak's
    "since" timestamp is NOT reset as long as misses stay under the limit."""
    since = None
    consecutive_misses = 0
    fired_at = []
    for t, present, is_down in series:
        if is_down:
            if since is None:
                since = t
            consecutive_misses = 0
            duration = t - since
            if duration >= duration_threshold:
                fired_at.append((t, duration))
        else:
            consecutive_misses += 1
            if consecutive_misses > miss_tolerance:
                since = None
                consecutive_misses = 0
            # else: within tolerance, streak survives this miss (since unchanged)
    return fired_at


def main(pitch_threshold: float, duration_threshold: float):
    print(f"pitch_threshold={pitch_threshold}  duration_threshold={duration_threshold}s\n")

    all_series = {}
    for subj in ["subject01", "subject06", "subject09", "subject24"]:
        all_series[subj] = get_is_down_series(subj, pitch_threshold)

    for miss_tolerance in [0, 1, 2, 3]:
        print(f"--- miss_tolerance={miss_tolerance} (forgive up to {miss_tolerance} "
              f"consecutive non-down poll(s) before resetting) ---")
        for subj, series in all_series.items():
            fired = simulate_with_tolerance(series, duration_threshold, miss_tolerance)
            down_count = sum(1 for _, present, is_down in series if is_down)
            present_count = sum(1 for _, present, _ in series if present)
            fired_str = ", ".join(f"{t:.1f}s(dur={d:.1f}s)" for t, d in fired) or "never"
            print(f"  {subj}: {down_count}/{len(series)} polls down, "
                  f"{present_count}/{len(series)} labeled phone-present -> fired: {fired_str}")
        print()


if __name__ == "__main__":
    pitch = float(sys.argv[1]) if len(sys.argv) > 1 else -35.0
    duration = float(sys.argv[2]) if len(sys.argv) > 2 else 25.0
    main(pitch, duration)
