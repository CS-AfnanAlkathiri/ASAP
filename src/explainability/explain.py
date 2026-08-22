"""
Per-prediction explainability for AI Support Student.

For Logistic Regression, the model produces one coefficient vector per
class (one-vs-rest style within the multinomial model). For a given
student's scaled feature vector x and predicted class c, each feature's
"contribution" to that class's score is:

    contribution_i = coef[c][i] * x_scaled[i]

This is the actual per-student decomposition of the linear decision
function for the predicted class -- not an invented heuristic. The sign
tells us the direction (increases vs decreases risk of the predicted
class) and the magnitude ranks importance for THIS student's prediction.

If the final model is not linear (see training fallback), permutation
importance is used instead as a global (not per-student) explanation,
and this is labeled clearly as such.
"""
from __future__ import annotations

import numpy as np
from sklearn.linear_model import LogisticRegression

from src.data.validation import FEATURE_COLUMNS


def explain_prediction(model, x_scaled: np.ndarray, predicted_class_idx: int, top_k: int = 4):
    """
    Args:
        model: fitted classifier (LogisticRegression expected for per-student explanations)
        x_scaled: 1D array, the scaled feature vector for one student (already
                  transformed by the same preprocessing pipeline used in training)
        predicted_class_idx: index of the predicted class (0=Low,1=Medium,2=High)
        top_k: number of top contributing factors to return

    Returns:
        dict with 'method', and 'factors' (list of {feature, direction, contribution})
    """
    if isinstance(model, LogisticRegression):
        coef = model.coef_[predicted_class_idx]  # shape (n_features,)
        contributions = coef * x_scaled
        order = np.argsort(-np.abs(contributions))[:top_k]
        factors = []
        for i in order:
            direction = "increases_risk_of_predicted_class" if contributions[i] > 0 else "decreases_risk_of_predicted_class"
            factors.append({
                "feature": FEATURE_COLUMNS[i],
                "direction": direction,
                "contribution": float(contributions[i]),
            })
        return {
            "method": "logistic_regression_coefficient_decomposition",
            "note": "Per-student contribution = class coefficient x this student's "
                    "scaled feature value. Direction is relative to the model's "
                    "predicted class, not a universal 'good/bad' judgment.",
            "factors": factors,
        }
    else:
        # Fallback: global permutation importance (not per-student).
        # Computed once at training time and cached; here we just report
        # that this is a global (not individualized) explanation.
        raise NotImplementedError(
            "Per-student explainability for non-linear models requires "
            "precomputed permutation importances; see training_metadata.json "
            "for global feature importance if a non-linear model was selected."
        )
