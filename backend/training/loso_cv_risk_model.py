"""Leave-one-subject-out cross-validation for the risk model (train_risk_model.py), addressing
priority item #2 in ai_examguard_thesis_scope_recommendations memory: the model's headline AUC
(0.879) is a single point estimate measured against just two held-out subjects (09, 11 -
VAL_SUBJECTS, reused from the phone-detector split by convention, not chosen for this purpose) out
of the 11 real subjects with any usable ground truth. That's too thin a basis to claim the number
generalizes - a different choice of 2 val subjects could easily have landed somewhere else, and
build_risk_windows.py's own docstring already documents one case (an earlier val split that scored
AUC 0.51 by accident of which cheat-event types those two subjects happened to have).

**What this measures instead**: refit the model 11 times, each time holding out one whole subject
(never just a random slice of windows - subjects are the real unit of generalization risk here,
since a held-out window from a subject that's otherwise in training barely tests anything new about
camera/lighting/individual pose habits). Report:
1. Per-subject held-out AUC where computable (some subjects have zero positive or zero negative
   windows - genuinely impossible to compute AUC there, reported as n/a with the reason, not
   silently skipped or treated as 0).
2. A POOLED LOSO AUC - every subject's held-out predictions concatenated into one array, one AUC
   computed over all of them. This is the headline "how well does this actually generalize to a new
   subject" number, and is the fair comparison to the original single-val-split 0.879.
3. A subject-level bootstrap 95% CI around the pooled AUC (resample which SUBJECTS contribute,
   with replacement, not which windows - windows within a subject are correlated with each other,
   so resampling at the window level would understate the real uncertainty).

Usage: ../../.venv/Scripts/python.exe loso_cv_risk_model.py [--C 1.0] [--bootstrap 2000]
"""
import argparse
import os

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score

FEATURES_CSV = os.path.join(os.path.dirname(__file__), "datasets", "risk-oep", "features.csv")
FEATURE_COLUMNS = ["face_lost_count", "phone_detected_count", "multiple_people_count"]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--C", type=float, default=1.0, help="inverse regularization strength, matches train_risk_model.py's default")
    parser.add_argument("--bootstrap", type=int, default=2000, help="number of subject-level bootstrap resamples for the CI")
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()

    if not os.path.isfile(FEATURES_CSV):
        raise SystemExit(f"{FEATURES_CSV} not found - run build_risk_windows.py first.")

    df = pd.read_csv(FEATURES_CSV)
    subjects = sorted(df["subject"].unique())
    print(f"{len(df)} windows across {len(subjects)} subjects, {df['label'].mean():.1%} overall positive rate\n")

    per_subject_true = {}
    per_subject_proba = {}

    print(f"{'subject':<12} {'n':>4} {'positives':>9} {'held-out AUC':>13}")
    for held_out in subjects:
        train_df = df[df["subject"] != held_out]
        test_df = df[df["subject"] == held_out]

        model = LogisticRegression(C=args.C, class_weight="balanced")
        model.fit(train_df[FEATURE_COLUMNS], train_df["label"])
        proba = model.predict_proba(test_df[FEATURE_COLUMNS])[:, 1]

        y_true = test_df["label"].to_numpy()
        per_subject_true[held_out] = y_true
        per_subject_proba[held_out] = proba

        n_pos = int(y_true.sum())
        n = len(y_true)
        if n_pos == 0:
            auc_str = "n/a (no positives)"
        elif n_pos == n:
            auc_str = "n/a (no negatives)"
        else:
            auc_str = f"{roc_auc_score(y_true, proba):.3f}"
        print(f"{held_out:<12} {n:>4} {n_pos:>9} {auc_str:>13}")

    # Pooled: every subject's held-out predictions, one AUC over all of them together.
    all_true = np.concatenate([per_subject_true[s] for s in subjects])
    all_proba = np.concatenate([per_subject_proba[s] for s in subjects])
    pooled_auc = roc_auc_score(all_true, all_proba)
    print(f"\nPooled LOSO-CV AUC (all {len(all_true)} held-out predictions, one number): {pooled_auc:.3f}")
    print("Compare against the original single-split val AUC of 0.879 (measured on just subject09/11) - "
          "this pooled number is the fairer 'does it generalize to a new subject' estimate.")

    # Subject-level bootstrap: resample WHICH SUBJECTS contribute, with replacement, not which
    # windows - a subject's windows are correlated (same room/lighting/person), so this is the
    # right unit to resample to get an honest uncertainty estimate given only 11 real subjects.
    rng = np.random.default_rng(args.seed)
    boot_aucs = []
    for _ in range(args.bootstrap):
        sample_subjects = rng.choice(subjects, size=len(subjects), replace=True)
        boot_true = np.concatenate([per_subject_true[s] for s in sample_subjects])
        boot_proba = np.concatenate([per_subject_proba[s] for s in sample_subjects])
        if boot_true.min() == boot_true.max():
            continue  # degenerate resample (all-same-class) - AUC undefined, skip and keep sampling
        boot_aucs.append(roc_auc_score(boot_true, boot_proba))

    boot_aucs = np.array(boot_aucs)
    lo, hi = np.percentile(boot_aucs, [2.5, 97.5])
    print(f"\nSubject-level bootstrap 95% CI ({len(boot_aucs)}/{args.bootstrap} valid resamples, "
          f"rest were degenerate all-one-class draws): [{lo:.3f}, {hi:.3f}]")
    print(f"Bootstrap mean: {boot_aucs.mean():.3f}, std: {boot_aucs.std():.3f}")


if __name__ == "__main__":
    main()
