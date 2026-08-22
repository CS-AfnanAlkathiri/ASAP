import pytest
from src.prediction.predict import RiskPredictor
from rag.vector_store.store import PolicyVectorStore
from rag.ingestion.ingest import ingest
from src.router.orchestrator import AdvisorRouter

VALID_FEATURES = {
    "Attendance_Percentage": 55,
    "Assignment_Submission_Rate": 40,
    "Quiz_Average_Score": 38,
    "Midterm_Score": 42,
    "Previous_GPA": 1.9,
    "Late_Submission_Count": 6,
    "Missing_Assignment_Count": 5,
    "Study_Plan_Adherence": 30,
}


@pytest.fixture(scope="module")
def router():
    predictor = RiskPredictor()
    chunks = ingest("documents/policies/Policies_and_Guidelines.pdf")
    store = PolicyVectorStore().build(chunks)
    return AdvisorRouter(predictor, store)


def test_advisor_report_contains_prediction_and_policy_context(router):
    report = router.get_advisor_report(VALID_FEATURES, student_id="STU-1", course_year=1)
    assert "risk_level" in report
    assert "policy_context" in report


def test_advisor_report_never_declares_intervention_required(router):
    report = router.get_advisor_report(VALID_FEATURES, student_id="STU-1", course_year=1)
    # Router output must not contain any field indicating an automatic
    # intervention decision.
    assert "intervention_required" not in report
    assert "action_taken" not in report


def test_advisor_report_includes_human_oversight_notice(router):
    report = router.get_advisor_report(VALID_FEATURES, student_id="STU-1", course_year=1)
    assert "human_oversight_notice" in report
    assert "advisor" in report["human_oversight_notice"].lower()


def test_direct_policy_query_does_not_touch_ml_model(router):
    result = router.query_policies("data privacy")
    assert "risk_level" not in result
    assert "results" in result


def test_custom_policy_query_overrides_default(router):
    report = router.get_advisor_report(
        VALID_FEATURES, student_id="STU-1", course_year=1,
        policy_query="cybersecurity vulnerability disable feature",
    )
    assert report["policy_query_used"] == "cybersecurity vulnerability disable feature"
