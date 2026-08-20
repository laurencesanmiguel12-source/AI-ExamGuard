"""Train the AI ExamGuard risk-score model: a logistic regression over windowed
face_lost/phone_detected/multiple_people counts, learned from real cheat-event ground truth
(build_risk_training_data.py's features.csv), replacing the previously hand-set weights for these
three signals in risk_service.WEIGHTS.

Logistic regression, not something more opaque, is a deliberate choice: it keeps the same kind of
transparency risk_service's original rule-based formula had (see the phase-9 scoping notes) - the
learned coefficients are still "how much does each signal move the risk score", just fit from real
data instead of guessed. Behavioral signals with no video ground truth available (tab-switch,
copy-paste, etc.) are NOT part of this model and stay hand-weighted in risk_service.py.

Also prints a comparison against the OLD hand-set weights (FACE_LOST=25, PHONE_DETECTED=30,
MULTIPLE_PEOPLE=25, capped at 100, thresholded at 50) evaluated on the same val windows, so the
improvement (or lack of one) from training is measured, not assumed.

**--final mode** (2026-08-01): fits on ALL subjects' windows instead of the original
train/(subject09,11)-val split, for the actual production model. This is safe to do now that
loso_cv_risk_model.py has already given an honest generalization estimate without needing a
permanently-reserved val set - the original split only existed to produce a single val number,
which LOSO-CV does better. --final prints an in-sample fit check only (NOT a real held-out metric -
restating that loudly so it's never mistaken for one) and points back to the LOSO-CV numbers as the
number to cite.

**2026-08-20 update**: dataset expanded from 11 to 24 real subjects (all remaining real OEP
subjects, previously sitting unextracted on disk - see ai_examguard_risk_model_dataset_expansion
memory). Production retrained on the full 24-subject set; current citable generalization estimate
is LOSO-CV's pooled AUC 0.813, 95% CI [0.712, 0.902] (tightened from 0.797/[0.666, 0.941] on 11
subjects) - update this note again if the dataset grows further.

Usage: ../../.venv/Scripts/python.exe train_risk_model.py [--C 1.0]
       ../../.venv/Scripts/python.exe train_risk_model.py --final   (production fit on all subjects)
"""
import argparse
import os

import joblib
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
)

FEATURES_CSV = os.path.join(os.path.dirname(__file__), "datasets", "risk-oep", "features.csv")
OUT_MODEL = os.path.join(os.path.dirname(__file__), "..", "app", "resources", "risk_model.joblib")

FEATURE_COLUMNS = ["face_lost_count", "phone_detected_count", "multiple_people_count"]

OLD_WEIGHTS = {"face_lost_count": 25, "phone_detected_count": 30, "multiple_people_count": 25}


def old_rule_predictions(df):
    raw = sum(df[col] * w for col, w in OLD_WEIGHTS.items())
    capped = raw.clip(upper=100)
    return (capped >= 50).astype(int)


def report(name, y_true, y_pred, y_proba=None):
    print(f"\n{name}:")
    print(f"  accuracy:  {accuracy_score(y_true, y_pred):.3f}")
    print(f"  precision: {precision_score(y_true, y_pred, zero_division=0):.3f}")
    print(f"  recall:    {recall_score(y_true, y_pred, zero_division=0):.3f}")
    print(f"  f1:        {f1_score(y_true, y_pred, zero_division=0):.3f}")
    if y_proba is not None:
        print(f"  roc-auc:   {roc_auc_score(y_true, y_proba):.3f}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--C", type=float, default=1.0, help="inverse regularization strength")
    parser.add_argument("--final", action="store_true",
                         help="fit on all 11 subjects for production, instead of the train/val split")
    args = parser.parse_args()

    if not os.path.isfile(FEATURES_CSV):
        raise SystemExit(f"{FEATURES_CSV} not found - run build_risk_training_data.py first.")

    df = pd.read_csv(FEATURES_CSV)

    if args.final:
        print(f"--final: fitting on all {len(df)} windows across {df['subject'].nunique()} subjects "
              f"({df['label'].mean():.1%} positive)")
        model = LogisticRegression(C=args.C, class_weight="balanced")
        model.fit(df[FEATURE_COLUMNS], df["label"])

        # In-sample only - NOT a real held-out metric. The honest generalization estimate is
        # loso_cv_risk_model.py's pooled AUC (0.797, 95% CI [0.666, 0.941] as of 2026-08-01) -
        # cite that, not this.
        in_sample_pred = model.predict(df[FEATURE_COLUMNS])
        in_sample_proba = model.predict_proba(df[FEATURE_COLUMNS])[:, 1]
        report("In-sample fit check ONLY - not a held-out metric, see loso_cv_risk_model.py for that",
               df["label"], in_sample_pred, in_sample_proba)

        print("\nLearned coefficients (log-odds per unit count):")
        for col, coef in zip(FEATURE_COLUMNS, model.coef_[0]):
            print(f"  {col}: {coef:+.3f}")
        print(f"  intercept: {model.intercept_[0]:+.3f}")

        os.makedirs(os.path.dirname(OUT_MODEL), exist_ok=True)
        joblib.dump(model, OUT_MODEL)
        print(f"\nModel saved to {OUT_MODEL}")
        return

    train_df = df[df["split"] == "train"]
    val_df = df[df["split"] == "val"]

    print(f"train: {len(train_df)} windows ({train_df['label'].mean():.1%} positive)")
    print(f"val:   {len(val_df)} windows ({val_df['label'].mean():.1%} positive)")

    model = LogisticRegression(C=args.C, class_weight="balanced")
    model.fit(train_df[FEATURE_COLUMNS], train_df["label"])

    val_pred = model.predict(val_df[FEATURE_COLUMNS])
    val_proba = model.predict_proba(val_df[FEATURE_COLUMNS])[:, 1]
    report("Trained logistic regression (val)", val_df["label"], val_pred, val_proba)

    old_pred = old_rule_predictions(val_df)
    report("Old hand-set weights, thresholded (val)", val_df["label"], old_pred)

    print("\nLearned coefficients (log-odds per unit count):")
    for col, coef in zip(FEATURE_COLUMNS, model.coef_[0]):
        print(f"  {col}: {coef:+.3f}")
    print(f"  intercept: {model.intercept_[0]:+.3f}")

    os.makedirs(os.path.dirname(OUT_MODEL), exist_ok=True)
    joblib.dump(model, OUT_MODEL)
    print(f"\nModel saved to {OUT_MODEL}")


if __name__ == "__main__":
    main()
