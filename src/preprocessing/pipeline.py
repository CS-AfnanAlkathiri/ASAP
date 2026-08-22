"""
Preprocessing pipeline for AI Support Student.

Strictly separates:
- X: exactly the 8 approved ML features
- Course_Year: contextual, carried alongside but NEVER fit/transformed into X
- Student_ID: identifier, never touched by the pipeline
- y: Academic_Risk_Level, label-encoded with a fixed class order

The pipeline (imputer + scaler) is fit ONLY on training data and reused
unchanged at inference time.
"""
from __future__ import annotations

import pandas as pd
import numpy as np
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler

from src.data.validation import FEATURE_COLUMNS, TARGET_COLUMN

# Fixed, meaningful class order (not alphabetical) so that downstream
# probability arrays are always in this order: Low, Medium, High.
RISK_CLASS_ORDER = ["Low Risk", "Medium Risk", "High Risk"]


def build_feature_pipeline() -> Pipeline:
    """Numeric preprocessing pipeline for the 8 ML features only."""
    return Pipeline(steps=[
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler", StandardScaler()),
    ])


def split_columns(df: pd.DataFrame):
    """
    Split a raw dataframe into its three strictly separated parts.
    Returns (X_raw, course_year, student_id, y_raw_or_None).
    y is None if TARGET_COLUMN is not present (e.g. inference-time input).
    """
    X_raw = df[FEATURE_COLUMNS].copy()
    course_year = df["Course_Year"].copy() if "Course_Year" in df.columns else None
    student_id = df["Student_ID"].copy() if "Student_ID" in df.columns else None
    y_raw = df[TARGET_COLUMN].copy() if TARGET_COLUMN in df.columns else None
    return X_raw, course_year, student_id, y_raw


def encode_labels(y_raw: pd.Series) -> np.ndarray:
    """Encode risk labels to integers using the fixed RISK_CLASS_ORDER."""
    mapping = {label: i for i, label in enumerate(RISK_CLASS_ORDER)}
    unknown = set(y_raw.unique()) - set(mapping)
    if unknown:
        raise ValueError(f"Unknown risk labels found: {unknown}")
    return y_raw.map(mapping).to_numpy()


def decode_label(index: int) -> str:
    return RISK_CLASS_ORDER[index]
