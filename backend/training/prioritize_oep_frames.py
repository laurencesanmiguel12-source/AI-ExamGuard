"""Cross-reference each OEP subject's gt.txt (cheat-event timestamps) against the frames already
extracted by extract_oep_frames.py, so annotation effort can start on frames that fall inside a
labeled cheat event rather than scrubbing through ~1000 frames per subject blind.

gt.txt format (undocumented in READ_ME.txt itself, but confirmed against the paper's Section IV -
Atoum et al., IEEE TMM 2017): tab-separated "start_time end_time cheat_type_code" per line, times
as zero-padded MMSS (e.g. "0135" = 1:35). The paper defines 5 cheat types: (1) reading from a
book/notes/paper, (2) talking to someone in the room, (3) using the Internet [detected via active
window count, not vision], (4) calling a friend over the phone, (5) using a phone. Only codes 4
and 5 mean a phone should actually be visible in frame - that's what PHONE_CODES below is for.

Code 6 shows up 18 times across the full 24-subject set and is NOT defined anywhere in the paper
(which only documents 1-5) - left as "other" here rather than guessed at.

A handful of gt.txt lines across the full 24-subject set contain malformed codes (5+ digit numbers
instead of 1-6) - skipped with a warning rather than guessed at.

Usage: ../../.venv/Scripts/python.exe prioritize_oep_frames.py [--fps 1]
"""
import argparse
import csv
import os

OEP_ROOT = r"C:\Users\maryj\Downloads\OEP_database\OEP database"
FRAMES_DIR = os.path.join(os.path.dirname(__file__), "datasets", "oep-msu", "raw_frames")
OUT_CSV = os.path.join(os.path.dirname(__file__), "datasets", "oep-msu", "frame_priority.csv")

PHONE_CODES = {4, 5}  # the only codes where a phone should be visible in frame - see docstring


def parse_mmss(s):
    s = s.strip()
    return int(s[:-2]) * 60 + int(s[-2:])


def load_events(subject_num):
    gt_path = os.path.join(OEP_ROOT, f"subject{subject_num}", "gt.txt")
    events = []
    with open(gt_path) as f:
        for line_no, line in enumerate(f, start=1):
            parts = line.split()
            if len(parts) != 3:
                continue
            start_raw, end_raw, code_raw = parts
            try:
                start, end, code = parse_mmss(start_raw), parse_mmss(end_raw), int(code_raw)
                if not (0 <= code <= 9):
                    raise ValueError("code out of expected 1-6 range")
            except ValueError:
                print(f"  subject{subject_num} gt.txt:{line_no}: skipping malformed line {line.strip()!r}")
                continue
            events.append((start, end, code))
    return events


def codes_at(events, t):
    return sorted({code for start, end, code in events if start <= t <= end})


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--fps", type=float, default=1.0, help="must match the --fps used in extract_oep_frames.py")
    args = parser.parse_args()

    if not os.path.isdir(FRAMES_DIR):
        raise SystemExit(f"{FRAMES_DIR} not found - run extract_oep_frames.py first.")

    rows = []
    subject_dirs = sorted(d for d in os.listdir(FRAMES_DIR) if d.startswith("subject"))

    for subject_dir in subject_dirs:
        subject_num = int(subject_dir.replace("subject", ""))
        events = load_events(subject_num)
        frame_dir = os.path.join(FRAMES_DIR, subject_dir)
        frame_files = sorted(f for f in os.listdir(frame_dir) if f.endswith(".jpg"))

        counts = {"phone": 0, "other_cheat": 0, "clean": 0}
        for i, fname in enumerate(frame_files):
            t = i / args.fps
            codes = codes_at(events, t)
            if any(c in PHONE_CODES for c in codes):
                priority = "phone"
            elif codes:
                priority = "other_cheat"
            else:
                priority = "clean"
            counts[priority] += 1
            rows.append({
                "subject": subject_dir,
                "frame_path": os.path.join(frame_dir, fname),
                "time_sec": round(t, 1),
                "cheat_codes": ";".join(str(c) for c in codes),
                "priority": priority,
            })
        print(
            f"{subject_dir}: {counts['phone']} phone-visible, {counts['other_cheat']} other-cheat, "
            f"{counts['clean']} clean (of {len(frame_files)} frames)"
        )

    with open(OUT_CSV, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["subject", "frame_path", "time_sec", "cheat_codes", "priority"])
        writer.writeheader()
        writer.writerows(rows)

    total_phone = sum(1 for r in rows if r["priority"] == "phone")
    total_other = sum(1 for r in rows if r["priority"] == "other_cheat")
    print(f"\n{total_phone} phone-visible / {total_other} other-cheat / {len(rows) - total_phone - total_other} clean, across {len(subject_dirs)} subjects")
    print(f"Manifest written to {OUT_CSV}")
    print(
        "\nSuggested annotation order: 'phone' rows first (codes 4/5 - a phone should actually be "
        "visible), then 'other_cheat' rows if you also want face-only examples of non-phone cheat "
        "behavior, then a random sample of 'clean' rows for negatives."
    )


if __name__ == "__main__":
    main()
