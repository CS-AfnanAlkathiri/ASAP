import pytest
from src.alerting.alert import compute_alert
from src.prediction.predict import RiskPredictor
from rag.vector_store.store import PolicyVectorStore
from rag.ingestion.ingest import ingest
from src.router.orchestrator import AdvisorRouter

HIGH_RISK_FEATURES = {
    "Attendance_Percentage": 55,
    "Assignment_Submission_Rate": 48,
    "Quiz_Average_Score": 40,
    "Midterm_Score": 38,
    "Previous_GPA": 1.9,
    "Late_Submission_Count": 7,
    "Missing_Assignment_Count": 6,
    "Study_Plan_Adherence": 30,
}

LOW_RISK_FEATURES = {
    "Attendance_Percentage": 95,
    "Assignment_Submission_Rate": 96,
    "Quiz_Average_Score": 90,
    "Midterm_Score": 88,
    "Previous_GPA": 3.7,
    "Late_Submission_Count": 0,
    "Missing_Assignment_Count": 0,
    "Study_Plan_Adherence": 92,
}


# --- Unit tests: the alert rule itself, no model/router needed ---

def test_alert_true_for_high_risk():
    assert compute_alert("High Risk") is True


def test_alert_false_for_medium_risk():
    # Deliberate: this is a level-only rule. A confident Medium Risk
    # prediction still does not alert. This is the known limitation
    # documented as a policy gap (Task 7), not a bug.
    assert compute_alert("Medium Risk") is False


def test_alert_false_for_low_risk():
    assert compute_alert("Low Risk") is False


# --- Integration tests: the field actually reaches the advisor report ---

@pytest.fixture(scope="module")
def router():
    predictor = RiskPredictor()
    chunks = ingest("documents/policies/Policies_and_Guidelines.pdf")
    store = PolicyVectorStore().build(chunks)
    return AdvisorRouter(predictor, store)


def test_high_risk_prediction_sets_alert_true(router):
    report = router.get_advisor_report(HIGH_RISK_FEATURES, student_id="STU-1", course_year=1)
    assert report["risk_level"] == "High Risk"
    assert report["high_risk_alert"] is True


def test_low_risk_prediction_sets_alert_false(router):
    report = router.get_advisor_report(LOW_RISK_FEATURES, student_id="STU-2", course_year=1)
    assert report["risk_level"] == "Low Risk"
    assert report["high_risk_alert"] is False


def test_alert_field_present_alongside_human_oversight_notice(router):
    # The alert flags a case for attention; it must never look like an
    # automated decision. Both fields should coexist on every report.
    report = router.get_advisor_report(HIGH_RISK_FEATURES, student_id="STU-1", course_year=1)
    assert "high_risk_alert" in report
    assert "human_oversight_notice" in report
    assert "intervention_required" not in report
