"""
Inference module: loads saved artifacts and produces a full prediction
result (risk level, class probabilities, contributing factors) for a
single student's approved feature values.

Course_Year and Student_ID are accepted as context but are NEVER passed
into the feature vector used by the model.
"""
from __future__ import annotations

import os
import joblib
import numpy as np
import pandas as pd

from src.data.validation import FEATURE_COLUMNS
from src.preprocessing.pipeline import RISK_CLASS_ORDER, decode_label
from src.explainability.explain import explain_prediction

MODELS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "models")


class RiskPredictor:
    def __init__(self, models_dir: str = MODELS_DIR):
        self.model = joblib.load(os.path.join(models_dir, "model.joblib"))
        self.pipeline = joblib.load(os.path.join(models_dir, "preprocessing_pipeline.joblib"))

    def predict(self, features: dict, student_id: str = None, course_year: int = None) -> dict:
        """
        Args:
            features: dict with EXACTLY the 8 FEATURE_COLUMNS keys.
            student_id: optional, passed through for display only.
            course_year: optional, passed through for display only, never
                         used as a model input.

        Returns a dict matching the API response contract.
        """
        missing = [c for c in FEATURE_COLUMNS if c not in features]
        if missing:
            raise ValueError(f"Missing required features: {missing}")

        # Build a single-row feature frame in the exact trained column order.
        x_raw = pd.DataFrame([[features[c] for c in FEATURE_COLUMNS]], columns=FEATURE_COLUMNS)
        x_scaled = self.pipeline.transform(x_raw)

        proba = self.model.predict_proba(x_scaled)[0]
        pred_idx = int(np.argmax(proba))
        risk_level = decode_label(pred_idx)

        class_probabilities = {
            RISK_CLASS_ORDER[i]: float(proba[i]) for i in range(len(RISK_CLASS_ORDER))
        }

        explanation = explain_prediction(self.model, x_scaled[0], pred_idx, top_k=4)

        return {
            "student_id": student_id,
            "course_year": course_year,
            "risk_level": risk_level,
            "risk_probability": float(proba[pred_idx]),
            "class_probabilities": class_probabilities,
            "contributing_factors": explanation["factors"],
            "explainability_method": explanation["method"],
            "explainability_note": explanation["note"],
        }
