"""Carve a genuinely frozen evaluation holdout out of annotation_batch/, separate from and in
addition to prepare_oep_split.py's train/val split.

**Why this exists**: subject09/subject11 (prepare_oep_split.py's VAL_SUBJECTS) are a legitimate
held-out set for training-time model selection (early stopping within a single run), but they have
also been reused, run after run, to decide whether each new candidate model should replace
production (run-3 vs run-4, run-4 vs run-5, and so on). Repeatedly using the same val set to make a
sequence of accept/reject decisions is a real leakage risk - closer to test-set hill-climbing than
genuine generalization evidence. Worse, several of those swap decisions ALSO checked accuracy
directly on the live-capture batches (backface_capture/backface_lit2/backface_100/backface4) that
the very same model had just been trained on - a training-set number, not a held-out one, reported
alongside the genuinely-held-out subject09/11 numbers without a clear label distinguishing the two.

All four of the OEP dataset's real phone-positive subjects (1, 6, 9, 24 - confirmed exhaustively
against gt.txt, see the 2026-07-28 project-status update) are already committed somewhere (1/6/24 in
train, 9 in val), so there is no fresh, never-touched real subject left to reserve. The practical fix
here is a stratified random slice pulled out of every current train-eligible source (each OEP subject
AND each live-capture batch, proportionally, fixed seed for reproducibility) and physically moved out
of annotation_batch/ into datasets/oep-msu/frozen_holdout/. subject09/11 are left untouched - they
stay in val, serving their existing, different purpose.

**The discipline that makes this meaningful (read before using this data)**:
- NEVER train on frozen_holdout/. It is not swept into split/train or split/val by
  prepare_oep_split.py because it no longer lives in annotation_batch/.
- NEVER use it to decide between candidate models mid-development, tune a confidence threshold, or
  pick which epoch/checkpoint to keep. That is what subject09/11 val is for.
- Only evaluate against it once per model that is a real swap candidate, when writing up a final
  comparison for the thesis report - and report the number even if it's unflattering.
- If you find yourself wanting to check frozen_holdout/ "just to see," that impulse is exactly the
  leakage this file exists to prevent - don't.

Usage: ../.venv/Scripts/python.exe make_frozen_holdout.py [--fraction 0.15] [--seed 20260730]
Re-running is a no-op if frozen_holdout/ already has content for a given source (won't re-sample or
duplicate) - pass --force to wipe and re-carve from scratch (only do this before ANY model has been
evaluated against the existing holdout; re-carving after evaluating burns the same leakage this
script exists to avoid).
"""
import argparse
import os
import random
import shutil

DATASET_DIR = os.path.join(os.path.dirname(__file__), "datasets", "oep-msu")
BATCH_DIR = os.path.join(DATASET_DIR, "annotation_batch")
HOLDOUT_DIR = os.path.join(DATASET_DIR, "frozen_holdout")

# Never pulled from - subject09/11 already serve as the training-time val split (a different,
# legitimate purpose) and shouldn't also be thinned out for this.
EXCLUDE_PREFIXES = ("subject09", "subject11")

SOURCE_PREFIXES = (
    "subject01", "subject02", "subject03", "subject04", "subject06",
    "subject10", "subject12", "subject13", "subject24",
    "backface_capture", "backface_lit2", "backface_100", "backface4",
)


def group_of(fname):
    for prefix in SOURCE_PREFIXES:
        if fname.startswith(prefix):
            return prefix
    return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--fraction", type=float, default=0.15)
    parser.add_argument("--seed", type=int, default=20260730)
    parser.add_argument("--force", action="store_true",
                         help="wipe frozen_holdout/ and re-carve from whatever's left in annotation_batch/ - "
                              "only safe before any model has been evaluated against it")
    args = parser.parse_args()

    if os.path.isdir(HOLDOUT_DIR) and os.listdir(HOLDOUT_DIR):
        if not args.force:
            print(f"{HOLDOUT_DIR} already has content - refusing to touch it. Pass --force to re-carve "
                  f"(only if nothing has evaluated against it yet).")
            return
        shutil.rmtree(HOLDOUT_DIR)

    os.makedirs(HOLDOUT_DIR, exist_ok=True)

    image_files = sorted(f for f in os.listdir(BATCH_DIR) if f.lower().endswith(".jpg"))
    groups = {}
    for fname in image_files:
        if fname.startswith(EXCLUDE_PREFIXES):
            continue
        g = group_of(fname)
        if g is None:
            print(f"WARNING: {fname} doesn't match any known source prefix - skipping (left in train)")
            continue
        groups.setdefault(g, []).append(fname)

    rng = random.Random(args.seed)
    total_moved = 0
    print(f"{'group':<20} {'total':>6} {'holdout':>8}")
    for g in sorted(groups):
        files = groups[g]
        rng.shuffle(files)
        n_holdout = max(1, round(len(files) * args.fraction))
        chosen = files[:n_holdout]
        for fname in chosen:
            stem = os.path.splitext(fname)[0]
            for ext in (".jpg", ".txt"):
                src = os.path.join(BATCH_DIR, stem + ext)
                if os.path.exists(src):
                    shutil.move(src, os.path.join(HOLDOUT_DIR, stem + ext))
        total_moved += n_holdout
        print(f"{g:<20} {len(files):>6} {n_holdout:>8}")

    print(f"\n{total_moved} frames moved to {HOLDOUT_DIR}")
    print("Remaining annotation_batch/ frames are unaffected and still feed prepare_oep_split.py's "
          "train/val split as before - rerun that script now to regenerate split/ without the holdout frames.")


if __name__ == "__main__":
    main()
