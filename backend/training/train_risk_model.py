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

Usage: ../../.venv/Scripts/python.exe train_risk_model.py [--C 1.0]
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
    args = parser.parse_args()

    if not os.path.isfile(FEATURES_CSV):
        raise SystemExit(f"{FEATURES_CSV} not found - run build_risk_training_data.py first.")

    df = pd.read_csv(FEATURES_CSV)
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
