import os
import time

import joblib
import pandas as pd

MODEL_PATH = os.path.join(
    os.path.dirname(__file__), "..", "resources", "risk_model.joblib"
)

FEATURE_ORDER = ["face_lost_count", "phone_detected_count", "multiple_people_count"]

# Trained by backend/training/train_risk_model.py on real cheat-event ground truth (MSU OEP
# dataset's gt.txt), not synthetic labels - see that script's docstring. Covers only the
# vision-based signals it can actually be grounded against (face lost, phone detected, multiple
# people); browser-behavior signals have no video equivalent and stay hand-weighted in
# risk_service.py.
_MODEL = joblib.load(MODEL_PATH)

# The OEP subjects were scripted/invoked to cheat, so the training set's positive rate (~65%) is
# nowhere near a real exam population's - the model's raw predict_proba(0, 0, 0) comes out to
# ~0.16, not 0, because its intercept encodes that inflated base rate. A session with zero
# detected violations should score 0, not a mystery baseline, so the raw probability is rescaled
# against that zero-evidence floor: floor maps to 0, and the (already near-1) max-evidence case
# stays near 1. This only recalibrates the output scale - it doesn't touch what the model learned
# about how the three signals relate to each other.
_ZERO_EVIDENCE_FLOOR = float(
    _MODEL.predict_proba(pd.DataFrame([[0, 0, 0]], columns=FEATURE_ORDER))[0][1]
)


class RiskModelService:

    @staticmethod
    def benchmark_latency_ms() -> float:
        start = time.perf_counter()
        RiskModelService.predict(0, 0, 0)
        return round((time.perf_counter() - start) * 1000, 1)

    @staticmethod
    def predict(face_lost_count: int, phone_detected_count: int, multiple_people_count: int) -> float:
        features = pd.DataFrame(
            [[face_lost_count, phone_detected_count, multiple_people_count]],
            columns=FEATURE_ORDER,
        )
        raw_probability = _MODEL.predict_proba(features)[0][1]
        scaled = (raw_probability - _ZERO_EVIDENCE_FLOOR) / (1 - _ZERO_EVIDENCE_FLOOR)
        return float(max(0.0, scaled) * 100)
