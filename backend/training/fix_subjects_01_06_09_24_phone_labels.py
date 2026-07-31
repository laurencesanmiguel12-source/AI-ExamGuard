"""Per-frame fix for the last unswept fairness-audit item: subjects 01/06/09/24, the four OEP
subjects gt.txt documents *real* phone-use for (see ai_examguard_fairness_audit_findings memory).
Unlike the other seven subjects (04/12/13/02/03/10/11), these four can't get a blanket phone-box
strip - they have a genuine mix of real held phones and the same OEP eye-tracking-camera confounder
already found elsewhere in this dataset. Every one of their 722 phone-positive frames was visually
reviewed (via build_phone_box_contact_sheets.py's contact sheets, full-resolution spot-checks on
ambiguous/multi-box cases) and classified individually.

**Method, stated plainly**: the eye-tracker device has a consistent, recognizable visual signature
(a metallic/silver or black clipped unit with a round lens, worn at the temple, connected by a
visible cord) and - critically - is never touched by a hand, since it's clipped on and static. A
genuine held phone always has a hand actively gripping it. This let single-phone-box frames be
classified reliably: an isolated box on the bare device with no hand present is bogus; a box
associated with a hand is genuine. All 114 bogus frames found this way are single-box frames - see
BOGUS_FRAMES below, one list entry per file, no per-box surgery needed since every bogus frame's
only phone box IS the bogus one.

Multi-box frames (many, especially for subject06/24 where the device and a genuine held phone often
appear in the same frame) were spot-checked at full resolution across a representative sample per
subject and, without exception, contained genuine hand-held-phone content - sometimes alongside a
redundant/duplicate device sub-box. Rather than attempting per-box surgery on ~250 more frames
(diminishing returns, real risk of mis-splitting), every multi-box frame is left untouched. This is
a disclosed simplification, not a blind assumption: it means a small number of multi-box frames
may still carry a redundant device box alongside the genuine one, a much smaller residual than the
single-box contamination this script removes.

Operates on every directory that can hold these subjects' labels: annotation_batch/,
split/train/labels/, split/val/labels/ (subject09/11 are VAL_SUBJECTS but none of 01/06/09/24 is -
included anyway for safety/future-proofing), and frozen_holdout/.

Usage: ../.venv/Scripts/python.exe fix_subjects_01_06_09_24_phone_labels.py           (dry run)
       ../.venv/Scripts/python.exe fix_subjects_01_06_09_24_phone_labels.py --apply    (fixes in place)
"""
import os
import sys

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OEP_DIR = os.path.join(BACKEND_DIR, "training", "datasets", "oep-msu")
ANNOTATION_BATCH_DIR = os.path.join(OEP_DIR, "annotation_batch")
TRAIN_LABELS_DIR = os.path.join(OEP_DIR, "split", "train", "labels")
VAL_LABELS_DIR = os.path.join(OEP_DIR, "split", "val", "labels")
HOLDOUT_DIR = os.path.join(OEP_DIR, "frozen_holdout")
REVIEW_OUT_DIR = os.path.join(OEP_DIR, "subject01_06_09_24_phone_strip_review")
BOGUS_LIST_PATH = os.path.join(OEP_DIR, "subject01_06_09_24_review_sheets", "bogus_frames.txt")

PHONE_CLASS = "0"

with open(BOGUS_LIST_PATH) as f:
    BOGUS_FRAMES = set(line.strip() for line in f if line.strip())


def strip_phone_boxes(lines):
    kept = [parts for parts in lines if parts[0] != PHONE_CLASS]
    return kept, len(lines) - len(kept)


def bogus_txt_names():
    return {os.path.splitext(fname)[0] + ".txt" for fname in BOGUS_FRAMES}


def process_dir(src_dir, dst_dir, in_place):
    if not os.path.isdir(src_dir):
        return [], [], 0

    targets = bogus_txt_names()
    txt_files = sorted(f for f in os.listdir(src_dir) if f in targets)

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
    print(f"{len(BOGUS_FRAMES)} frames flagged bogus across subjects 01/06/09/24")

    if not apply:
        os.makedirs(REVIEW_OUT_DIR, exist_ok=True)
        txt_files, touched, dropped = process_dir(ANNOTATION_BATCH_DIR, REVIEW_OUT_DIR, in_place=False)
        print(f"DRY RUN - fixed labels written to {REVIEW_OUT_DIR} for spot-check")
        print(f"{len(txt_files)} bogus-listed label files found in annotation_batch/")
        print(f"{len(touched)} files had their (sole) phone box stripped, {dropped} boxes total dropped")
        if len(txt_files) != len(BOGUS_FRAMES):
            missing = bogus_txt_names() - set(txt_files)
            print(f"WARNING: {len(missing)} bogus-listed files not found in annotation_batch/: "
                  f"{sorted(missing)[:10]}{'...' if len(missing) > 10 else ''}")
        print("\nRe-run with --apply once this looks right to fix annotation_batch/, "
              "split/train/labels/, split/val/labels/, and frozen_holdout/ in place.")
        return

    for label, src_dir in (
        ("annotation_batch/", ANNOTATION_BATCH_DIR),
        ("split/train/labels/", TRAIN_LABELS_DIR),
        ("split/val/labels/", VAL_LABELS_DIR),
        ("frozen_holdout/", HOLDOUT_DIR),
    ):
        txt_files, touched, dropped = process_dir(src_dir, src_dir, in_place=True)
        print(f"{label}: {len(txt_files)} files scanned, {len(touched)} fixed, {dropped} phone boxes dropped")


if __name__ == "__main__":
    main()
