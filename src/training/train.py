"""
Training script for AI Support Student.

- Loads and validates the dataset
- Splits into train/test with stratification on the target
- Fits preprocessing ONLY on training data
- Trains Logistic Regression (primary, interpretable) and compares against
  Random Forest and Gradient Boosting as candidates
- Selects the final model based on balanced accuracy + High Risk recall +
  interpretability, and saves all artifacts

Run: python -m src.training.train
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone

import joblib
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.metrics import (
    accuracy_score, balanced_accuracy_score, precision_recall_fscore_support,
    confusion_matrix, classification_report,
)

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from src.data.validation import load_dataset, validate_dataset, FEATURE_COLUMNS
from src.preprocessing.pipeline import (
    build_feature_pipeline, split_columns, encode_labels, RISK_CLASS_ORDER,
)

RANDOM_SEED = 42
DATA_PATH = os.path.join("data", "dataset.csv")
MODELS_DIR = "models"
MODEL_VERSION = "1.0.0"


def evaluate_model(name, model, X_test, y_test):
    y_pred = model.predict(X_test)
    acc = accuracy_score(y_test, y_pred)
    bal_acc = balanced_accuracy_score(y_test, y_pred)
    precision, recall, f1, support = precision_recall_fscore_support(
        y_test, y_pred, labels=[0, 1, 2], zero_division=0
    )
    cm = confusion_matrix(y_test, y_pred, labels=[0, 1, 2])
    report = classification_report(
        y_test, y_pred, labels=[0, 1, 2], target_names=RISK_CLASS_ORDER,
        zero_division=0, output_dict=True,
    )
    per_class = {
        RISK_CLASS_ORDER[i]: {
            "precision": float(precision[i]),
            "recall": float(recall[i]),
            "f1": float(f1[i]),
            "support": int(support[i]),
        } for i in range(3)
    }
    result = {
        "name": name,
        "accuracy": float(acc),
        "balanced_accuracy": float(bal_acc),
        "high_risk_recall": per_class["High Risk"]["recall"],
        "per_class": per_class,
        "confusion_matrix": cm.tolist(),
        "classification_report": report,
    }
    return result


def main():
    print("=== Loading and validating dataset ===")
    df = load_dataset(DATA_PATH)
    report = validate_dataset(df)
    print(report.summary())
    if not report.is_clean():
        print("WARNING: dataset did not pass all validation checks. Proceeding "
              "cautiously; review the summary above.")
    for w in report.warnings:
        print(f"[data warning] {w}")

    print("\n=== Splitting columns (strict role separation) ===")
    X_raw, course_year, student_id, y_raw = split_columns(df)
    y = encode_labels(y_raw)
    print(f"X shape: {X_raw.shape} (exactly {len(FEATURE_COLUMNS)} features expected)")
    assert list(X_raw.columns) == FEATURE_COLUMNS, "Feature set mismatch!"
    assert "Student_ID" not in X_raw.columns
    assert "Course_Year" not in X_raw.columns

    print("\n=== Train/test split (stratified, seed=%d) ===" % RANDOM_SEED)
    X_train, X_test, y_train, y_test, cy_train, cy_test, sid_train, sid_test = train_test_split(
        X_raw, y, course_year, student_id,
        test_size=0.2, random_state=RANDOM_SEED, stratify=y,
    )
    print(f"Train: {X_train.shape[0]} rows, Test: {X_test.shape[0]} rows")
    print("Train class distribution:", np.bincount(y_train))
    print("Test class distribution:", np.bincount(y_test))

    print("\n=== Fitting preprocessing pipeline on TRAIN ONLY ===")
    feature_pipeline = build_feature_pipeline()
    X_train_proc = feature_pipeline.fit_transform(X_train)
    X_test_proc = feature_pipeline.transform(X_test)

    print("\n=== Training candidate models ===")
    candidates = {
        "logistic_regression": LogisticRegression(
            max_iter=2000, random_state=RANDOM_SEED,
            class_weight="balanced",
        ),
        "random_forest": RandomForestClassifier(
            n_estimators=300, random_state=RANDOM_SEED, class_weight="balanced",
        ),
        "gradient_boosting": GradientBoostingClassifier(random_state=RANDOM_SEED),
    }

    results = {}
    fitted = {}
    for name, model in candidates.items():
        model.fit(X_train_proc, y_train)
        fitted[name] = model
        results[name] = evaluate_model(name, model, X_test_proc, y_test)
        r = results[name]
        print(f"\n[{name}] accuracy={r['accuracy']:.3f} "
              f"balanced_accuracy={r['balanced_accuracy']:.3f} "
              f"high_risk_recall={r['high_risk_recall']:.3f}")

    # Model selection: Logistic Regression is the interpretable baseline.
    # We select it as final unless a candidate clearly and meaningfully
    # outperforms it on balanced accuracy AND High Risk recall, since
    # interpretability is a hard requirement for the advisor-support use case.
    lr_result = results["logistic_regression"]
    best_name = "logistic_regression"
    best_result = lr_result
    for name in ["random_forest", "gradient_boosting"]:
        r = results[name]
        if (r["balanced_accuracy"] > lr_result["balanced_accuracy"] + 0.03
                and r["high_risk_recall"] > lr_result["high_risk_recall"] + 0.03):
            if r["balanced_accuracy"] > best_result["balanced_accuracy"]:
                best_name = name
                best_result = r

    print(f"\n=== Selected final model: {best_name} ===")
    if best_name != "logistic_regression":
        print("NOTE: a non-linear model outperformed Logistic Regression by a "
              "meaningful margin on both balanced accuracy and High Risk recall; "
              "explainability will fall back to permutation importance.")
    final_model = fitted[best_name]

    os.makedirs(MODELS_DIR, exist_ok=True)
    joblib.dump(final_model, os.path.join(MODELS_DIR, "model.joblib"))
    joblib.dump(feature_pipeline, os.path.join(MODELS_DIR, "preprocessing_pipeline.joblib"))

    metadata = {
        "model_version": MODEL_VERSION,
        "model_type": best_name,
        "trained_at_utc": datetime.now(timezone.utc).isoformat(),
        "random_seed": RANDOM_SEED,
        "feature_columns": FEATURE_COLUMNS,
        "risk_class_order": RISK_CLASS_ORDER,
        "train_rows": int(X_train.shape[0]),
        "test_rows": int(X_test.shape[0]),
        "all_candidate_results": results,
        "selected_model_result": best_result,
        "data_validation_summary": {
            "n_rows": report.n_rows,
            "class_distribution": report.class_distribution,
            "warnings": report.warnings,
        },
    }
    with open(os.path.join(MODELS_DIR, "training_metadata.json"), "w") as f:
        json.dump(metadata, f, indent=2)

    print(f"\nSaved model -> {MODELS_DIR}/model.joblib")
    print(f"Saved preprocessing pipeline -> {MODELS_DIR}/preprocessing_pipeline.joblib")
    print(f"Saved training metadata -> {MODELS_DIR}/training_metadata.json")

    return metadata


if __name__ == "__main__":
    main()
