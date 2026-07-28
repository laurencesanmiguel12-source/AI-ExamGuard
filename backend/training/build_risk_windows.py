"""Turn cached per-poll detections (extract_risk_polls.py's polls.csv) into windowed
face_lost/phone_detected/multiple_people counts, labeled against real MSU OEP gt.txt cheat-event
ground truth. Fast enough to rerun freely while iterating on the labeling rule below, unlike the
detector pass in extract_risk_polls.py.

gt.txt defines 5 cheat types (see prioritize_oep_frames.py's docstring for the full code
reference, confirmed against the paper): (1) reading notes, (2) talking to someone, (3) using the
internet, (4) phone call, (5) phone use. Only some of these have any correlate a webcam-based
vision system could plausibly see:
- codes 4/5 (phone) - directly what PHONE_DETECTED targets
- code 2 (talking to someone) - the "real-exam" subjects' cheat events were invoked by the proctor
  "talking, walking up to the student, or handing them a book" (READ_ME.txt), so a second body
  plausibly enters frame - treated as a MULTIPLE_PEOPLE-plausible positive
Codes 1 (reading notes), 3 (internet use), and 6 (undefined in the paper) have NO plausible visual
correlate at all - reading notes doesn't reliably move the face out of frame or bring a second
person into view, and internet use is completely invisible to a webcam. A window whose ONLY
overlapping cheat code is one of these three is EXCLUDED from the dataset rather than forced into
either label - the vision-only feature set structurally cannot confirm or deny it, and forcing a
label either way would just train the model against noise it can't actually see.

(First pass at this script labeled ANY overlapping code as positive, which meant the two held-out
val subjects - one all "talking", one mostly "reading notes" - tested almost entirely on cheat
types with no visual signal, and the trained model scored ~random, AUC 0.51, on them. Restricting
the label to vision-plausible codes is the fix, not more data - code 1/3/6 events are structurally
invisible no matter how many subjects get added.)

A trailing WINDOW_SECONDS window (matching risk_service.WINDOW_SECONDS) is slid over each subject's
poll sequence, counting how many polls in the window flagged each event type - this mirrors exactly
what RiskService.compute_risk counts from real Violation rows in production. Split by SUBJECT, not
window, to avoid leakage - reuses the VAL_SUBJECTS convention from prepare_oep_split.py.

Usage: ../../.venv/Scripts/python.exe build_risk_windows.py
"""
import csv
import os
from collections import defaultdict

OEP_ROOT = r"C:\Users\maryj\Downloads\OEP_database\OEP database"
POLLS_CSV = os.path.join(os.path.dirname(__file__), "datasets", "risk-oep", "polls.csv")
OUT_CSV = os.path.join(os.path.dirname(__file__), "datasets", "risk-oep", "features.csv")

VAL_SUBJECTS = {"subject09", "subject11"}
WINDOW_SECONDS = 120

VISION_PLAUSIBLE_CODES = {2, 4, 5}
AMBIGUOUS_CODES = {1, 3, 6}

FIELDNAMES = [
    "subject", "window_end_sec", "face_lost_count", "phone_detected_count",
    "multiple_people_count", "label", "split",
]


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
            except ValueError:
                print(f"  subject{subject_num} gt.txt:{line_no}: skipping malformed line {line.strip()!r}")
                continue
            events.append((start, end, code))
    return events


def label_for_window(events, start_t, end_t):
    overlapping_codes = {code for e_start, e_end, code in events if e_start <= end_t and e_end >= start_t}
    if overlapping_codes & VISION_PLAUSIBLE_CODES:
        return 1
    if overlapping_codes:
        return None  # only ambiguous (non-visual) codes overlap - exclude, don't guess
    return 0


def load_polls():
    by_subject = defaultdict(list)
    with open(POLLS_CSV) as f:
        for row in csv.DictReader(f):
            by_subject[row["subject"]].append((
                int(row["time_sec"]),
                bool(int(row["face_lost"])),
                bool(int(row["phone_detected"])),
                int(row["person_count"]) > 1,
            ))
    for subject in by_subject:
        by_subject[subject].sort()
    return by_subject


def main():
    if not os.path.isfile(POLLS_CSV):
        raise SystemExit(f"{POLLS_CSV} not found - run extract_risk_polls.py first.")

    polls_by_subject = load_polls()

    all_windows = []
    excluded_total = 0
    for subject_dir, polls in sorted(polls_by_subject.items()):
        subject_num = int(subject_dir.replace("subject", ""))
        events = load_events(subject_num)

        windows = []
        excluded = 0
        for end_t, _, _, _ in polls:
            start_t = end_t - WINDOW_SECONDS
            label = label_for_window(events, start_t, end_t)
            if label is None:
                excluded += 1
                continue
            windowed = [p for p in polls if start_t <= p[0] <= end_t]
            windows.append({
                "subject": subject_dir,
                "window_end_sec": end_t,
                "face_lost_count": sum(1 for p in windowed if p[1]),
                "phone_detected_count": sum(1 for p in windowed if p[2]),
                "multiple_people_count": sum(1 for p in windowed if p[3]),
                "label": label,
                "split": "val" if subject_dir in VAL_SUBJECTS else "train",
            })

        pos = sum(w["label"] for w in windows)
        rate = f"{pos / len(windows):.1%}" if windows else "n/a"
        print(f"{subject_dir}: {len(windows)} windows ({excluded} excluded), {pos} positive ({rate})")
        all_windows.extend(windows)
        excluded_total += excluded

    with open(OUT_CSV, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(all_windows)

    train_n = sum(1 for w in all_windows if w["split"] == "train")
    val_n = sum(1 for w in all_windows if w["split"] == "val")
    print(
        f"\n{len(all_windows)} windows total ({train_n} train / {val_n} val), "
        f"{excluded_total} excluded (non-visual-only codes) -> {OUT_CSV}"
    )


if __name__ == "__main__":
    main()
