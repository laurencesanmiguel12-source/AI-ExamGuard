"""Densely sample frames around the OEP dataset's labeled phone-use windows (cheat_type codes 4/5
- see prioritize_oep_frames.py's docstring for how those were confirmed against the paper).

Phone-visible content in OEP is scarce (110 seconds total across all 24 subjects), so unlike
extract_oep_frames.py's uniform 1fps pass across a whole ~15min session, this targets just the
known phone-event windows (padded by a few seconds on each side, to catch the phone coming in/out
of view rather than only the exact labeled boundary) at a much higher sample rate, to get as much
distinct signal as possible out of the little footage that exists.

Usage: ../../.venv/Scripts/python.exe extract_oep_phone_windows.py [--subjects 6,9,24] [--fps 5] [--pad 3]
"""
import argparse
import os

import cv2

from extract_oep_frames import OEP_ROOT, OUT_DIR, find_webcam_avi

PHONE_CODES = {4, 5}


def parse_mmss(s):
    s = s.strip()
    return int(s[:-2]) * 60 + int(s[-2:])


def phone_windows(subject_num, pad):
    gt_path = os.path.join(OEP_ROOT, f"subject{subject_num}", "gt.txt")
    raw = []
    with open(gt_path) as f:
        for line in f:
            parts = line.split()
            if len(parts) != 3:
                continue
            try:
                start, end, code = parse_mmss(parts[0]), parse_mmss(parts[1]), int(parts[2])
            except ValueError:
                continue
            if code in PHONE_CODES:
                raw.append((max(0, start - pad), end + pad))

    if not raw:
        return []

    raw.sort()
    merged = [raw[0]]
    for start, end in raw[1:]:
        last_start, last_end = merged[-1]
        if start <= last_end:
            merged[-1] = (last_start, max(last_end, end))
        else:
            merged.append((start, end))
    return merged


def extract_windows(subject_num, windows, sample_fps):
    subject_dir = os.path.join(OEP_ROOT, f"subject{subject_num}")
    webcam_path = find_webcam_avi(subject_dir)

    cap = cv2.VideoCapture(webcam_path)
    video_fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    frame_interval = max(1, round(video_fps / sample_fps))

    out_subdir = os.path.join(OUT_DIR, f"subject{subject_num:02d}")
    os.makedirs(out_subdir, exist_ok=True)

    saved = 0
    for start_sec, end_sec in windows:
        start_frame = int(start_sec * video_fps)
        end_frame = int(end_sec * video_fps)
        cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)

        frame_idx = start_frame
        while frame_idx <= end_frame:
            ok, frame = cap.read()
            if not ok:
                break
            if (frame_idx - start_frame) % frame_interval == 0:
                t = frame_idx / video_fps
                out_path = os.path.join(
                    out_subdir, f"subject{subject_num:02d}_phonewin_{t:07.2f}s.jpg"
                )
                cv2.imwrite(out_path, frame)
                saved += 1
            frame_idx += 1
    cap.release()
    return saved


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--subjects", type=str, default="6,9,24")
    parser.add_argument("--fps", type=float, default=5.0, help="sample rate within phone windows")
    parser.add_argument("--pad", type=float, default=3.0, help="seconds of padding on each side of a labeled window")
    args = parser.parse_args()
    subjects = [int(s) for s in args.subjects.split(",")]

    total = 0
    for subject_num in subjects:
        windows = phone_windows(subject_num, args.pad)
        if not windows:
            print(f"subject{subject_num:02d}: no phone events found, skipping")
            continue
        saved = extract_windows(subject_num, windows, args.fps)
        total += saved
        window_desc = ", ".join(f"{s:.0f}-{e:.0f}s" for s, e in windows)
        print(f"subject{subject_num:02d}: {saved} frames from window(s) [{window_desc}]")

    print(f"\n{total} phone-window frames extracted to {OUT_DIR}")


if __name__ == "__main__":
    main()
