from fastapi.testclient import TestClient
from api.main import app, load_artifacts

# TestClient does not always trigger startup events reliably across
# versions, so we load artifacts explicitly before building the client.
load_artifacts()
client = TestClient(app)

VALID_PAYLOAD = {
    "student_id": "STU-XXXXXXXX",
    "course_year": 3,
    "attendance_percentage": 72,
    "assignment_submission_rate": 68,
    "quiz_average_score": 74,
    "midterm_score": 65,
    "previous_gpa": 2.8,
    "late_submission_count": 4,
    "missing_assignment_count": 2,
    "study_plan_adherence": 60,
}


def test_health_endpoint():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_predict_endpoint_success():
    resp = client.post("/predict", json=VALID_PAYLOAD)
    assert resp.status_code == 200
    body = resp.json()
    assert body["risk_level"] in ["Low Risk", "Medium Risk", "High Risk"]
    assert body["student_id"] == "STU-XXXXXXXX"
    assert body["course_year"] == 3


def test_predict_endpoint_probabilities_valid():
    resp = client.post("/predict", json=VALID_PAYLOAD)
    body = resp.json()
    total = sum(body["class_probabilities"].values())
    assert abs(total - 1.0) < 1e-6


def test_predict_endpoint_missing_field_returns_422():
    bad_payload = dict(VALID_PAYLOAD)
    del bad_payload["previous_gpa"]
    resp = client.post("/predict", json=bad_payload)
    assert resp.status_code == 422


def test_predict_endpoint_out_of_range_returns_422():
    bad_payload = dict(VALID_PAYLOAD)
    bad_payload["attendance_percentage"] = 150
    resp = client.post("/predict", json=bad_payload)
    assert resp.status_code == 422


def test_predict_response_includes_human_oversight_notice():
    resp = client.post("/predict", json=VALID_PAYLOAD)
    body = resp.json()
    assert "human_oversight_notice" in body
    assert "advisor" in body["human_oversight_notice"].lower()


def test_policy_query_endpoint():
    resp = client.post("/policy/query", json={"query": "data privacy", "top_k": 2})
    assert resp.status_code == 200
    body = resp.json()
    assert body["found"] is True
    assert len(body["results"]) <= 2


def test_policy_query_endpoint_no_match():
    resp = client.post("/policy/query", json={"query": "chocolate cake recipe for tonight dinner"})
    body = resp.json()
    assert body["found"] is False
    assert body["results"] == []
