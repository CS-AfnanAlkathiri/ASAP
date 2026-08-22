import pandas as pd
import numpy as np
from src.data.validation import load_dataset, FEATURE_COLUMNS
from src.preprocessing.pipeline import (
    build_feature_pipeline, split_columns, encode_labels, decode_label, RISK_CLASS_ORDER,
)

DATA_PATH = "data/dataset.csv"


def test_split_columns_excludes_id_and_context_from_features():
    df = load_dataset(DATA_PATH)
    X, course_year, student_id, y = split_columns(df)
    assert "Student_ID" not in X.columns
    assert "Course_Year" not in X.columns
    assert list(X.columns) == FEATURE_COLUMNS


def test_exactly_eight_features_reach_model_input():
    df = load_dataset(DATA_PATH)
    X, _, _, _ = split_columns(df)
    assert X.shape[1] == 8


def test_course_year_preserved_separately():
    df = load_dataset(DATA_PATH)
    _, course_year, _, _ = split_columns(df)
    assert course_year is not None
    assert course_year.name == "Course_Year"


def test_student_id_preserved_separately():
    df = load_dataset(DATA_PATH)
    _, _, student_id, _ = split_columns(df)
    assert student_id is not None
    assert student_id.name == "Student_ID"


def test_label_encoding_round_trip():
    y_raw = pd.Series(["Low Risk", "Medium Risk", "High Risk"])
    y_enc = encode_labels(y_raw)
    assert list(y_enc) == [0, 1, 2]
    for i, label in enumerate(RISK_CLASS_ORDER):
        assert decode_label(i) == label


def test_unknown_label_raises():
    y_raw = pd.Series(["Not A Real Risk"])
    try:
        encode_labels(y_raw)
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_pipeline_fit_transform_shapes():
    df = load_dataset(DATA_PATH)
    X, _, _, _ = split_columns(df)
    pipeline = build_feature_pipeline()
    X_proc = pipeline.fit_transform(X)
    assert X_proc.shape == (len(X), 8)
    # scaled features should have ~0 mean, ~1 std on the fitted data
    assert np.allclose(X_proc.mean(axis=0), 0, atol=1e-6)
    assert np.allclose(X_proc.std(axis=0), 1, atol=1e-6)
