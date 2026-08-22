import pytest
from src.prediction.predict import RiskPredictor
from src.preprocessing.pipeline import RISK_CLASS_ORDER

VALID_FEATURES = {
    "Attendance_Percentage": 72,
    "Assignment_Submission_Rate": 68,
    "Quiz_Average_Score": 74,
    "Midterm_Score": 65,
    "Previous_GPA": 2.8,
    "Late_Submission_Count": 4,
    "Missing_Assignment_Count": 2,
    "Study_Plan_Adherence": 60,
}


@pytest.fixture(scope="module")
def predictor():
    return RiskPredictor()


def test_predictor_loads(predictor):
    assert predictor.model is not None
    assert predictor.pipeline is not None


def test_predict_returns_valid_risk_class(predictor):
    result = predictor.predict(VALID_FEATURES, student_id="STU-1", course_year=2)
    assert result["risk_level"] in RISK_CLASS_ORDER


def test_class_probabilities_sum_to_one(predictor):
    result = predictor.predict(VALID_FEATURES, student_id="STU-1", course_year=2)
    total = sum(result["class_probabilities"].values())
    assert abs(total - 1.0) < 1e-6


def test_class_probabilities_all_three_classes_present(predictor):
    result = predictor.predict(VALID_FEATURES, student_id="STU-1", course_year=2)
    assert set(result["class_probabilities"].keys()) == set(RISK_CLASS_ORDER)


def test_probabilities_in_valid_range(predictor):
    result = predictor.predict(VALID_FEATURES, student_id="STU-1", course_year=2)
    for p in result["class_probabilities"].values():
        assert 0.0 <= p <= 1.0
    assert 0.0 <= result["risk_probability"] <= 1.0


def test_missing_feature_raises(predictor):
    incomplete = dict(VALID_FEATURES)
    del incomplete["Previous_GPA"]
    with pytest.raises(ValueError):
        predictor.predict(incomplete)


def test_student_id_and_course_year_passthrough_only(predictor):
    """Two students with identical features but different IDs/course years
    must receive identical predictions -- proving these fields don't
    influence the model."""
    r1 = predictor.predict(VALID_FEATURES, student_id="STU-AAAA", course_year=1)
    r2 = predictor.predict(VALID_FEATURES, student_id="STU-BBBB", course_year=4)
    assert r1["risk_level"] == r2["risk_level"]
    assert r1["class_probabilities"] == r2["class_probabilities"]
    assert r1["student_id"] != r2["student_id"]
    assert r1["course_year"] != r2["course_year"]


def test_contributing_factors_present_and_bounded(predictor):
    result = predictor.predict(VALID_FEATURES, student_id="STU-1", course_year=2)
    factors = result["contributing_factors"]
    assert 1 <= len(factors) <= 4
    for f in factors:
        assert "feature" in f and "direction" in f and "contribution" in f


def test_high_risk_profile_predicts_high_risk(predictor):
    """A student with poor values across the board should be flagged High Risk."""
    poor = {
        "Attendance_Percentage": 40,
        "Assignment_Submission_Rate": 30,
        "Quiz_Average_Score": 25,
        "Midterm_Score": 20,
        "Previous_GPA": 1.2,
        "Late_Submission_Count": 8,
        "Missing_Assignment_Count": 6,
        "Study_Plan_Adherence": 20,
    }
    result = predictor.predict(poor, student_id="STU-POOR", course_year=1)
    assert result["risk_level"] == "High Risk"


def test_low_risk_profile_predicts_low_risk(predictor):
    strong = {
        "Attendance_Percentage": 98,
        "Assignment_Submission_Rate": 97,
        "Quiz_Average_Score": 92,
        "Midterm_Score": 90,
        "Previous_GPA": 3.9,
        "Late_Submission_Count": 0,
        "Missing_Assignment_Count": 0,
        "Study_Plan_Adherence": 95,
    }
    result = predictor.predict(strong, student_id="STU-STRONG", course_year=4)
    assert result["risk_level"] == "Low Risk"
