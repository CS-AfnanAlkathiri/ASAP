"""
FastAPI backend for AI Support Student.

Endpoints:
  GET  /health           - liveness check
  POST /predict           - full advisor report (ML prediction + policy context)
  POST /policy/query      - direct policy/guideline lookup (RAG only)

This is a decision-SUPPORT API. It never returns an "intervention
required" decision -- see human_oversight_notice in every /predict
response.
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from typing import Optional, List, Dict

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.prediction.predict import RiskPredictor
from rag.vector_store.store import PolicyVectorStore
from src.router.orchestrator import AdvisorRouter

MODELS_DIR = os.path.join(os.path.dirname(__file__), "..", "models")
STORE_PATH = os.path.join(os.path.dirname(__file__), "..", "rag", "vector_store", "policy_store.pkl")

app = FastAPI(
    title="AI Support Student API",
    description="Advisor-support academic early-warning system. "
                 "Decision support only -- a human Program Advisor makes all final decisions.",
    version="1.0.0",
)

_predictor: Optional[RiskPredictor] = None
_policy_store: Optional[PolicyVectorStore] = None
_router: Optional[AdvisorRouter] = None


@app.on_event("startup")
def load_artifacts():
    global _predictor, _policy_store, _router
    _predictor = RiskPredictor(models_dir=MODELS_DIR)
    _policy_store = PolicyVectorStore.load(STORE_PATH)
    _router = AdvisorRouter(_predictor, _policy_store)


class PredictRequest(BaseModel):
    student_id: str = Field(..., description="Pseudonymous identifier, display/linking only")
    course_year: int = Field(..., ge=1, le=4, description="Contextual only; not a model input")
    attendance_percentage: float = Field(..., ge=0, le=100)
    assignment_submission_rate: float = Field(..., ge=0, le=100)
    quiz_average_score: float = Field(..., ge=0, le=100)
    midterm_score: float = Field(..., ge=0, le=100)
    previous_gpa: float = Field(..., ge=0, le=4)
    late_submission_count: float = Field(..., ge=0)
    missing_assignment_count: float = Field(..., ge=0)
    study_plan_adherence: float = Field(..., ge=0, le=100)
    policy_query: Optional[str] = Field(
        None, description="Optional custom policy question; defaults to a "
                           "risk-level-appropriate query if omitted."
    )

    def to_feature_dict(self) -> dict:
        return {
            "Attendance_Percentage": self.attendance_percentage,
            "Assignment_Submission_Rate": self.assignment_submission_rate,
            "Quiz_Average_Score": self.quiz_average_score,
            "Midterm_Score": self.midterm_score,
            "Previous_GPA": self.previous_gpa,
            "Late_Submission_Count": self.late_submission_count,
            "Missing_Assignment_Count": self.missing_assignment_count,
            "Study_Plan_Adherence": self.study_plan_adherence,
        }


class ContributingFactor(BaseModel):
    feature: str
    direction: str
    contribution: float


class PolicyContextItem(BaseModel):
    chunk_id: int
    title: str
    content: str
    source: str
    relevance_score: float


class PredictResponse(BaseModel):
    student_id: str
    course_year: int
    risk_level: str
    risk_probability: float
    high_risk_alert: bool
    class_probabilities: Dict[str, float]
    contributing_factors: List[ContributingFactor]
    explainability_method: str
    explainability_note: str
    policy_context: List[PolicyContextItem]
    policy_query_used: str
    human_oversight_notice: str
    model_version: str
    prediction_timestamp_utc: str


class PolicyQueryRequest(BaseModel):
    query: str
    top_k: int = 3


class PolicyQueryResponse(BaseModel):
    query: str
    results: List[PolicyContextItem]
    found: bool
    note: Optional[str] = None


@app.get("/health")
def health():
    return {"status": "ok", "model_loaded": _predictor is not None,
            "policy_store_loaded": _policy_store is not None}


@app.post("/predict", response_model=PredictResponse)
def predict(request: PredictRequest):
    if _router is None:
        raise HTTPException(status_code=503, detail="Model/policy store not loaded yet")
    try:
        report = _router.get_advisor_report(
            features=request.to_feature_dict(),
            student_id=request.student_id,
            course_year=request.course_year,
            policy_query=request.policy_query,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    report["model_version"] = "1.0.0"
    report["prediction_timestamp_utc"] = datetime.now(timezone.utc).isoformat()
    return report


@app.post("/policy/query", response_model=PolicyQueryResponse)
def policy_query(request: PolicyQueryRequest):
    if _router is None:
        raise HTTPException(status_code=503, detail="Policy store not loaded yet")
    return _router.query_policies(request.query, top_k=request.top_k)
