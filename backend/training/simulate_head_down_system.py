"""System-level (not frame-level) validation for PROLONGED_HEAD_DOWN: runs the real
_track_head_down state machine against the 4 densely timestamped phonewin sequences, resampled
to approximate the real 5s-poll production cadence.

KNOWN LIMITATION, discovered 2026-07-31, don't trust this script's "fired N times" output for
duration-threshold questions: _track_head_down computes duration via datetime.now() internally,
but this loop runs through the frames' *simulated* video timestamps in real (fast) wall-clock
time - so accumulated duration never actually reaches HEAD_DOWN_DURATION_THRESHOLD_SECONDS
during a run of this script, regardless of how long the real streak "should" have been. The
streak-BREAKING observation this script surfaced (a single miss discarding an otherwise-long
streak, motivating HEAD_DOWN_MISS_TOLERANCE) is still valid, since that's duration-independent -
but the actual before/after fire verdict came from simulate_head_down_tolerance.py instead,
which reimplements the state machine locally using the frames' own timestamps (`duration = t -
since`) rather than calling datetime.now(). Kept this script for the streak-count trace it
prints (useful for seeing exactly where/why a streak breaks), not for its fire count.
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


class FakeSession:
    head_down_since = None
    head_down_consecutive_count = 0
    head_down_miss_streak = 0
    head_down_violation_logged = False


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
    """Picks the frame closest to each interval_s tick, starting from the first frame's
    timestamp - approximates what a real 5s poller would actually see."""
    if not frames:
        return []
    start = frames[0][0]
    end = frames[-1][0]
    picks = []
    t = start
    idx = 0
    while t <= end:
        # advance idx to the frame closest to t
        best = min(frames, key=lambda f: abs(f[0] - t))
        picks.append(best)
        t += interval_s
    return picks


def simulate(subject: str, pitch_threshold: float, duration_threshold: float):
    frames = load_sequence(subject)
    if not frames:
        print(f"{subject}: no frames found")
        return

    polls = resample_at_poll_interval(frames)
    print(f"=== {subject}: {len(frames)} raw frames -> {len(polls)} simulated 5s polls "
          f"({polls[0][0]:.1f}s - {polls[-1][0]:.1f}s) ===")

    face_service.HEAD_DOWN_PITCH_THRESHOLD_DEGREES = pitch_threshold
    face_service.HEAD_DOWN_DURATION_THRESHOLD_SECONDS = duration_threshold

    session = FakeSession()
    fired_at = []
    for t, jpg_path, present in polls:
        image = cv2.imread(jpg_path)
        detection = face_service._detect_largest_face(image)
        pose = face_service._estimate_head_pose(image, detection) if detection is not None else None
        fallback = (
            face_service._head_present_via_pose_fallback(image) if detection is None else False
        )
        _, should_log = face_service._track_head_down(session, pose, fallback)
        marker = "P" if present else "."
        if should_log:
            fired_at.append(t)
            marker = "!FIRE!"
        print(f"    t={t:7.1f}s label_phone={marker:>6} pitch={pose['pitch'] if pose else 'NA':>8} "
              f"fallback={fallback} streak_count={session.head_down_consecutive_count}")

    print(f"  --> fired {len(fired_at)} time(s): {[f'{t:.1f}s' for t in fired_at]}")
    print()


if __name__ == "__main__":
    pitch = float(sys.argv[1]) if len(sys.argv) > 1 else -35.0
    duration = float(sys.argv[2]) if len(sys.argv) > 2 else 25.0
    for subj in ["subject01", "subject06", "subject09", "subject24"]:
        simulate(subj, pitch, duration)
