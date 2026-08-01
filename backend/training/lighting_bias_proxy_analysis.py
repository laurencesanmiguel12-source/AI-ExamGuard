"""A real, honest FIRST slice of the demographic bias audit (thesis-scope item #1's "still open"
half - see ai_examguard_thesis_scope_recommendations memory). Not a substitute for it: the OEP
dataset has zero demographic metadata (no skin tone/gender/age/camera-quality labels, confirmed
exhaustively - see fairness_audit.py's own docstring), so a genuine demographic audit needs real
subjects recruited specifically with known, labeled attributes - a human-subjects data collection
exercise, not something this script or any script can manufacture from existing anonymized data.

What this DOES measure, honestly: mean image brightness per group (every real OEP subject, every
live-capture batch), correlated against that same group's phone-detection precision/recall and
face-detection rate from fairness_audit.py's most recent run. Lighting is a well-documented proxy
in the CV-fairness literature (poor lighting disproportionately degrades detection for darker skin
tones specifically, e.g. the Buolamwini/Gebru "Gender Shades" finding) - a real, measurable,
disclosed signal worth checking BEFORE the real demographic audit happens, not a replacement for
it. If brightness correlates with performance here, that's a concrete, evidenced reason to
prioritize recruiting across lighting conditions specifically when the real audit is scoped.

Usage: ../.venv/Scripts/python.exe lighting_bias_proxy_analysis.py
"""
import os

import cv2
import numpy as np

BATCH_DIR = os.path.join(os.path.dirname(__file__), "datasets", "oep-msu", "annotation_batch")
HOLDOUT_DIR = os.path.join(os.path.dirname(__file__), "datasets", "oep-msu", "frozen_holdout")

GROUP_PREFIXES = (
    "subject01", "subject02", "subject03", "subject04", "subject06", "subject09",
    "subject10", "subject11", "subject12", "subject13", "subject24",
    "backface_capture", "backface_lit2", "backface_100", "backface4",
)

# Copied from the 2026-08-01 corrected fairness_audit.py run (commit e15cc9a) - presence
# precision/recall (the real production-behavior numbers) and face detection rate, per group.
# Keep in sync by hand if fairness_audit.py is re-run and numbers change.
LATEST_FAIRNESS_NUMBERS = {
    "backface4": (0.950, 0.844, 0.990),
    "backface_100": (0.957, 0.880, 1.000),
    "backface_capture": (1.000, 1.000, 1.000),
    "backface_lit2": (1.000, 0.933, 1.000),
    "subject01": (0.990, 0.924, 1.000),
    "subject02": (float("nan"), float("nan"), 1.000),
    "subject03": (0.000, float("nan"), 1.000),
    "subject04": (float("nan"), float("nan"), 1.000),
    "subject06": (0.942, 0.898, 0.988),
    "subject09": (0.939, 0.995, 1.000),
    "subject10": (0.000, float("nan"), 0.856),
    "subject11": (0.000, float("nan"), 0.934),
    "subject12": (0.000, float("nan"), 0.968),
    "subject13": (0.000, float("nan"), 0.908),
    "subject24": (0.967, 0.993, 1.000),
}


def group_of(fname):
    for prefix in GROUP_PREFIXES:
        if fname.startswith(prefix):
            return prefix
    return None


def mean_brightness(img_path):
    image = cv2.imread(img_path)
    if image is None:
        return None
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    return float(np.mean(gray))


def main():
    groups = {}
    for source_dir in (BATCH_DIR, HOLDOUT_DIR):
        for fname in sorted(os.listdir(source_dir)):
            if not fname.lower().endswith(".jpg"):
                continue
            g = group_of(fname)
            if g is None:
                continue
            groups.setdefault(g, []).append(os.path.join(source_dir, fname))

    rows = []
    for g in sorted(groups):
        brightness_values = [mean_brightness(p) for p in groups[g]]
        brightness_values = [b for b in brightness_values if b is not None]
        if not brightness_values:
            continue
        mean_b = float(np.mean(brightness_values))
        std_b = float(np.std(brightness_values))
        prec, rec, face_rate = LATEST_FAIRNESS_NUMBERS.get(g, (float("nan"),) * 3)
        rows.append((g, len(brightness_values), mean_b, std_b, prec, rec, face_rate))

    print(f"{'group':<20} {'n':>4} {'mean_bright':>11} {'std':>6} {'prec':>7} {'recall':>7} {'face_rate':>9}")
    for g, n, mean_b, std_b, prec, rec, fr in rows:
        prec_s = f"{prec:.3f}" if prec == prec else "n/a"
        rec_s = f"{rec:.3f}" if rec == rec else "n/a"
        print(f"{g:<20} {n:>4} {mean_b:>11.1f} {std_b:>6.1f} {prec_s:>7} {rec_s:>7} {fr:>9.3f}")

    # Correlation between brightness and recall/face_rate, over groups with a computable recall
    valid = [(mean_b, rec, fr) for _, _, mean_b, _, _, rec, fr in rows if rec == rec]
    if len(valid) >= 3:
        brights, recs, frs = zip(*valid)
        corr_rec = float(np.corrcoef(brights, recs)[0, 1])
        corr_fr = float(np.corrcoef(brights, [f for f in frs])[0, 1])
        print(f"\nPearson correlation, brightness vs phone-recall (n={len(valid)} groups): {corr_rec:+.3f}")
        print(f"Pearson correlation, brightness vs face-detection-rate (n={len(valid)} groups): {corr_fr:+.3f}")
        print("(|r| > 0.5 is a real, worth-investigating relationship; near 0 means brightness "
              "alone doesn't explain the spread seen in fairness_audit.py's output)")
    else:
        print("\nNot enough groups with a computable recall to correlate.")


if __name__ == "__main__":
    main()
