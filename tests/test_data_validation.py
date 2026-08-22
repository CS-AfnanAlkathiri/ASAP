import pandas as pd
from src.data.validation import load_dataset, validate_dataset, FEATURE_COLUMNS, TARGET_COLUMN

DATA_PATH = "data/dataset.csv"


def test_dataset_loads():
    df = load_dataset(DATA_PATH)
    assert len(df) > 0


def test_required_columns_present():
    df = load_dataset(DATA_PATH)
    report = validate_dataset(df)
    assert report.missing_columns == []


def test_no_missing_values():
    df = load_dataset(DATA_PATH)
    report = validate_dataset(df)
    assert report.missing_values == {}


def test_no_duplicate_student_ids():
    df = load_dataset(DATA_PATH)
    report = validate_dataset(df)
    assert report.duplicate_student_ids == 0


def test_all_risk_labels_valid():
    df = load_dataset(DATA_PATH)
    report = validate_dataset(df)
    assert report.invalid_risk_labels == []


def test_values_within_expected_ranges():
    df = load_dataset(DATA_PATH)
    report = validate_dataset(df)
    assert report.out_of_range == {}


def test_exactly_eight_feature_columns_defined():
    assert len(FEATURE_COLUMNS) == 8


def test_target_column_name():
    assert TARGET_COLUMN == "Academic_Risk_Level"


def test_missing_column_detected():
    df = pd.DataFrame({"Student_ID": ["a"], "Academic_Risk_Level": ["Low Risk"]})
    report = validate_dataset(df)
    assert len(report.missing_columns) > 0
