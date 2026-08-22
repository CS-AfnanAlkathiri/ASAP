"""
Risk Assessment & Alert Module (Y.3172 'P' node).

Deliberately minimal: TR-09/TR-10 require the system to assess the ML
result against a "high-risk condition" and generate an alert. TR-22
requires that condition to be *configurable*, not an arbitrary
hard-coded threshold -- and explicitly does NOT require it to be
statistically validated, because "unvalidated risk thresholds" are
listed as out of scope for the MVP.

This module implements the simplest defensible rule: alert on the
predicted risk LEVEL only (currently "High Risk"). It does not use
prediction confidence/probability as a second signal. That is a known,
stated limitation -- see the policy-gap write-up (Task 7) for the case
this simple rule does not resolve (e.g. a high-confidence Medium Risk
prediction).

This module makes no intervention decision. It only flags a case for
advisor attention -- see HUMAN_OVERSIGHT_NOTICE in orchestrator.py.
"""
from __future__ import annotations

# Configurable, per TR-22. Change this set to alter which predicted
# risk levels are treated as alert-worthy. Kept as a plain module-level
# constant (not buried in logic) so it's easy to find and to justify
# in the report.
ALERT_TRIGGER_CLASSES = {"High Risk"}


def compute_alert(risk_level: str) -> bool:
    """
    Return True if the predicted risk level meets the current
    high-risk alert condition.

    This is a level-only rule -- it does not consider
    class_probabilities/confidence. A confident Medium Risk prediction
    and a barely-confident Medium Risk prediction are treated
    identically. See module docstring.
    """
    return risk_level in ALERT_TRIGGER_CLASSES
