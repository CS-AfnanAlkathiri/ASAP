"""
Dataset loading and validation for the AI Support Student system.

This module enforces the column-role contract defined in the project spec:
- Student_ID: identifier only (never a feature)
- Course_Year: contextual only (never a feature)
- 8 named columns: ML features (X)
- Academic_Risk_Level: target (y)

It performs structural validation (columns, types, ranges, duplicates,
missing values, class distribution) and raises clear errors when the
dataset does not match the expected contract.
"""
from __future__ import annotations

import pandas as pd
from dataclasses import dataclass, field

ID_COLUMN = "Student_ID"
CONTEXT_COLUMN = "Course_Year"
TARGET_COLUMN = "Academic_Risk_Level"

FEATURE_COLUMNS = [
    "Attendance_Percentage",
    "Assignment_Submission_Rate",
    "Quiz_Average_Score",
    "Midterm_Score",
    "Previous_GPA",
    "Late_Submission_Count",
    "Missing_Assignment_Count",
    "Study_Plan_Adherence",
]

REQUIRED_COLUMNS = [ID_COLUMN, CONTEXT_COLUMN] + FEATURE_COLUMNS + [TARGET_COLUMN]

VALID_RISK_LEVELS = {"Low Risk", "Medium Risk", "High Risk"}

EXPECTED_RANGES = {
    "Attendance_Percentage": (0, 100),
    "Assignment_Submission_Rate": (0, 100),
    "Quiz_Average_Score": (0, 100),
    "Midterm_Score": (0, 100),
    "Previous_GPA": (0, 4),
    "Late_Submission_Count": (0, None),
    "Missing_Assignment_Count": (0, None),
    "Study_Plan_Adherence": (0, 100),
    "Course_Year": (1, 4),
}


@dataclass
class ValidationReport:
    n_rows: int = 0
    n_columns: int = 0
    missing_columns: list = field(default_factory=list)
    extra_columns: list = field(default_factory=list)
    missing_values: dict = field(default_factory=dict)
    duplicate_rows: int = 0
    duplicate_student_ids: int = 0
    out_of_range: dict = field(default_factory=dict)
    invalid_risk_labels: list = field(default_factory=list)
    class_distribution: dict = field(default_factory=dict)
    warnings: list = field(default_factory=list)

    def is_clean(self) -> bool:
        return (
            not self.missing_columns
            and not self.out_of_range
            and not self.invalid_risk_labels
            and self.duplicate_student_ids == 0
        )

    def summary(self) -> str:
        lines = [
            f"Rows: {self.n_rows}, Columns: {self.n_columns}",
            f"Missing required columns: {self.missing_columns or 'none'}",
            f"Extra (ignored) columns: {self.extra_columns or 'none'}",
            f"Missing values by column: {self.missing_values or 'none'}",
            f"Duplicate rows: {self.duplicate_rows}",
            f"Duplicate Student_IDs: {self.duplicate_student_ids}",
            f"Out-of-range values: {self.out_of_range or 'none'}",
            f"Invalid risk labels: {self.invalid_risk_labels or 'none'}",
            f"Class distribution: {self.class_distribution}",
        ]
        if self.warnings:
            lines.append("Warnings:")
            lines.extend(f"  - {w}" for w in self.warnings)
        return "\n".join(lines)


def load_dataset(path: str) -> pd.DataFrame:
    """Load the raw CSV without modification."""
    return pd.read_csv(path)


def validate_dataset(df: pd.DataFrame) -> ValidationReport:
    """
    Validate structural integrity of the dataset against the fixed
    column-role contract. Does NOT modify the dataframe.
    """
    report = ValidationReport()
    report.n_rows, report.n_columns = df.shape

    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    extra = [c for c in df.columns if c not in REQUIRED_COLUMNS]
    report.missing_columns = missing
    report.extra_columns = extra
    if extra:
        report.warnings.append(
            f"Extra columns present and will be ignored (not used as features "
            f"unless explicitly instructed): {extra}"
        )

    if missing:
        # Cannot safely proceed with range/label checks if required columns absent.
        report.warnings.append(
            "Required columns missing; skipping downstream range/label checks."
        )
        return report

    # Missing values
    nulls = df[REQUIRED_COLUMNS].isnull().sum()
    report.missing_values = {c: int(n) for c, n in nulls.items() if n > 0}

    # Duplicates
    report.duplicate_rows = int(df.duplicated().sum())
    report.duplicate_student_ids = int(df[ID_COLUMN].duplicated().sum())

    # Range checks
    out_of_range = {}
    for col, (lo, hi) in EXPECTED_RANGES.items():
        series = df[col]
        bad = series[(series < lo) | ((hi is not None) & (series > hi))]
        if len(bad) > 0:
            out_of_range[col] = int(len(bad))
    report.out_of_range = out_of_range

    # Target label validity
    bad_labels = sorted(set(df[TARGET_COLUMN].unique()) - VALID_RISK_LEVELS)
    report.invalid_risk_labels = bad_labels

    # Class distribution
    report.class_distribution = df[TARGET_COLUMN].value_counts().to_dict()

    # Potential leakage heuristic: flag any feature that perfectly separates
    # the target (i.e. every class has a completely non-overlapping range).
    # This is a heuristic warning only, not an automatic exclusion.
    for col in FEATURE_COLUMNS:
        ranges = df.groupby(TARGET_COLUMN)[col].agg(["min", "max"])
        overlaps = False
        rows = ranges.to_numpy()
        for i in range(len(rows)):
            for j in range(len(rows)):
                if i == j:
                    continue
                lo_i, hi_i = rows[i]
                lo_j, hi_j = rows[j]
                if not (hi_i < lo_j or hi_j < lo_i):
                    overlaps = True
        if not overlaps:
            report.warnings.append(
                f"Potential target leakage: '{col}' ranges do not overlap across "
                f"risk classes. Review before trusting this feature's importance."
            )

    return report
