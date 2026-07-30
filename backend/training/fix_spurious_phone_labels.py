"""Fix a labeling defect found while investigating why subject04/12/13 scored badly in the
2026-07-30 fairness audit (see ai_examguard_frozen_holdout_eval / fairness_audit.py):
**every one of their 179 "phone" boxes is spurious.**

Visually reviewed all 179 phone-positive frames across these three subjects (9 contact sheets,
full coverage, not a sample) and found zero genuine held phones. The boxes fall into three
categories, all wrongly labeled class 0 ("phone") by the original auto-labeler and never caught by
human review for these subjects: (1) the OEP study's own wired clip-on eye-tracking camera, mounted
on the subject's glasses - the same confounder previously found and fixed for subject01 only (see
fix_subject01_face_duplicate_boxes.py's docstring) but never swept to the rest of the dataset;
(2) background clutter - blank wall/locker sections, a proctor's arm/silhouette; (3) a handheld pen
misidentified as a phone in a couple of frames.

This lines up with the dataset's own ground truth: gt.txt only documents real phone-use cheat
events for subjects 1, 6, 9, and 24 (confirmed exhaustively across all 24 subjects, see the
2026-07-28 project-status update) - subjects 04/12/13 were never expected to have genuine
phone-positive frames at all. Given that and the 100% spurious rate found on full visual review,
this removes every phone-class box for these three subjects rather than attempting a finer-grained
per-box heuristic (a geometric "is this near the face" filter was considered and rejected - a real
held phone can also appear near the face/ear in this dataset, so it can't reliably tell the device
apart from a genuine phone-to-ear pose; only direct visual review can, and that's what this script
encodes the result of, not what it tries to automate).

Face boxes (class 1) are untouched - YuNet's face detections were never in question here.

Operates on every directory that can hold these subjects' labels: annotation_batch/ (the reviewed
ground truth), split/train/labels/ (prepare_oep_split.py's copy - subjects 04/12/13 aren't
VAL_SUBJECTS, so always land in train), and frozen_holdout/ (make_frozen_holdout.py's evaluation
set - these subjects had frames stratified into it too, and leaving bogus phone boxes there would
mean the frozen holdout itself stays contaminated, undermining the whole point of building it).

Usage: ../.venv/Scripts/python.exe fix_spurious_phone_labels.py           (dry run, writes to review dir)
       ../.venv/Scripts/python.exe fix_spurious_phone_labels.py --apply    (fixes all three dirs in place)
"""
import os
import sys

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OEP_DIR = os.path.join(BACKEND_DIR, "training", "datasets", "oep-msu")
ANNOTATION_BATCH_DIR = os.path.join(OEP_DIR, "annotation_batch")
TRAIN_LABELS_DIR = os.path.join(OEP_DIR, "split", "train", "labels")
HOLDOUT_DIR = os.path.join(OEP_DIR, "frozen_holdout")
REVIEW_OUT_DIR = os.path.join(OEP_DIR, "subject04_12_13_phone_strip_review")

AFFECTED_SUBJECTS = ("subject04", "subject12", "subject13")
PHONE_CLASS = "0"


def strip_phone_boxes(lines):
    kept = [parts for parts in lines if parts[0] != PHONE_CLASS]
    return kept, len(lines) - len(kept)


def process_dir(src_dir, dst_dir, in_place):
    if not os.path.isdir(src_dir):
        return [], [], 0

    txt_files = sorted(
        f for f in os.listdir(src_dir)
        if f.endswith(".txt") and any(f.startswith(s) for s in AFFECTED_SUBJECTS)
    )

    total_dropped = 0
    files_touched = []
    for fname in txt_files:
        src_path = os.path.join(src_dir, fname)
        with open(src_path) as f:
            lines = [l.split() for l in f if l.strip()]

        kept_lines, dropped = strip_phone_boxes(lines)
        if dropped:
            total_dropped += dropped
            files_touched.append((fname, dropped))

        out_path = os.path.join(dst_dir, fname) if not in_place else src_path
        if dropped or not in_place:
            os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
            with open(out_path, "w") as f:
                if kept_lines:
                    f.write("\n".join(" ".join(parts) for parts in kept_lines) + "\n")

    return txt_files, files_touched, total_dropped


def main():
    apply = "--apply" in sys.argv

    if not apply:
        os.makedirs(REVIEW_OUT_DIR, exist_ok=True)
        txt_files, touched, dropped = process_dir(ANNOTATION_BATCH_DIR, REVIEW_OUT_DIR, in_place=False)
        print(f"DRY RUN - fixed labels written to {REVIEW_OUT_DIR} for spot-check")
        print(f"{len(txt_files)} subject04/12/13 label files scanned in annotation_batch/")
        print(f"{len(touched)} files had every phone box stripped, {dropped} boxes total dropped")
        print("\nRe-run with --apply once this looks right to fix annotation_batch/, "
              "split/train/labels/, and frozen_holdout/ in place.")
        return

    for label, src_dir in (
        ("annotation_batch/", ANNOTATION_BATCH_DIR),
        ("split/train/labels/", TRAIN_LABELS_DIR),
        ("frozen_holdout/", HOLDOUT_DIR),
    ):
        txt_files, touched, dropped = process_dir(src_dir, src_dir, in_place=True)
        print(f"{label}: {len(txt_files)} files scanned, {len(touched)} fixed, {dropped} phone boxes dropped")


if __name__ == "__main__":
    main()
