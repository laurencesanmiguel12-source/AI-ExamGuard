"""Second pass of the same label-sweep started in fix_spurious_phone_labels.py (subject04/12/13) -
this time covering subject02, subject03, subject10, and subject11, the four other OEP subjects
not in gt.txt's real phone-use list (only subjects 1/6/9/24 have any documented phone-use cheat
event). subject11 is one of prepare_oep_split.py's VAL_SUBJECTS, making this fix directly relevant
to every training run's val metrics, not just train.

Visually reviewed all 341 phone-positive frames across these four subjects (18 contact sheets, full
coverage) and found zero genuine held phones - same result as the first pass. The boxes break down
into the same categories, plus one new variant found this round: (1) the same wired clip-on
eye-tracking camera confounder as before, by far the majority; (2) a handful of frames where the
ENTIRE cap/head is boxed as "phone" (subject10 specifically, who wears a baseball cap - no visible
mechanism for why, just an auto-labeler artifact, possibly triggered by the cap's dark rectangular
brim); (3) background clutter - blank wall/locker sections, a proctor visible in the background.

Combined with the first pass, all seven of OEP's non-priority subjects (02/03/04/10/11/12/13) have
now been fully swept - see ai_examguard_fairness_audit_findings memory for the fairness-audit angle
that started this thread. The remaining four subjects (01/06/09/24, the ones gt.txt actually
documents real phone-use for) were NOT touched here and need a different approach if reviewed - they
have a genuine mix of real and possibly-spurious boxes, so blanket stripping isn't safe there the
way it is for these seven.

Usage: ../.venv/Scripts/python.exe fix_spurious_phone_labels_batch2.py           (dry run, writes to review dir)
       ../.venv/Scripts/python.exe fix_spurious_phone_labels_batch2.py --apply    (fixes all three dirs in place)
"""
import os
import sys

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OEP_DIR = os.path.join(BACKEND_DIR, "training", "datasets", "oep-msu")
ANNOTATION_BATCH_DIR = os.path.join(OEP_DIR, "annotation_batch")
TRAIN_LABELS_DIR = os.path.join(OEP_DIR, "split", "train", "labels")
VAL_LABELS_DIR = os.path.join(OEP_DIR, "split", "val", "labels")
HOLDOUT_DIR = os.path.join(OEP_DIR, "frozen_holdout")
REVIEW_OUT_DIR = os.path.join(OEP_DIR, "subject02_03_10_11_phone_strip_review")

AFFECTED_SUBJECTS = ("subject02", "subject03", "subject10", "subject11")
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
        print(f"{len(txt_files)} subject02/03/10/11 label files scanned in annotation_batch/")
        print(f"{len(touched)} files had every phone box stripped, {dropped} boxes total dropped")
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
