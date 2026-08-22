"""
Router/orchestrator for AI Support Student.

Coordinates two strictly separate components:
  1. ML prediction (RiskPredictor) -- answers "what is the predicted risk?"
  2. Policy RAG (PolicyVectorStore) -- answers "what do the policies say?"

The router does NOT let RAG content influence the prediction, and does
NOT let the ML prediction influence which policies are retrieved beyond
using the predicted risk LEVEL (not the raw features) to select a
sensible default policy query. It also does not make any intervention
decision -- it only assembles information for the Program Advisor.
"""
from __future__ import annotations

from src.prediction.predict import RiskPredictor
from rag.vector_store.store import PolicyVectorStore
from src.alerting.alert import compute_alert

# Default policy queries keyed by risk level, used only to surface
# generally relevant guidance alongside a prediction when the advisor
# hasn't asked a specific policy question. These are UI convenience
# defaults, not model-driven behavior.
DEFAULT_POLICY_QUERY_BY_RISK = {
    "Low Risk": "student data privacy minimal data use",
    "Medium Risk": "human oversight advisor review explainability",
    "High Risk": "human oversight intervention advisor decision accountability",
}

HUMAN_OVERSIGHT_NOTICE = (
    "This is a decision-support output only. The AI system does not decide "
    "that intervention is required. The Program Advisor must independently "
    "review this information and decide whether to intervene, refer the "
    "student elsewhere, take another action, or take no action."
)


class AdvisorRouter:
    def __init__(self, predictor: RiskPredictor, policy_store: PolicyVectorStore):
        self.predictor = predictor
        self.policy_store = policy_store

    def get_advisor_report(self, features: dict, student_id: str = None,
                            course_year: int = None, policy_query: str = None,
                            top_k_policies: int = 3) -> dict:
        """
        Full orchestrated report: ML prediction + explainability + relevant
        policy context, assembled for the advisor. Never emits an
        intervention decision.
        """
        prediction = self.predictor.predict(
            features, student_id=student_id, course_year=course_year
        )

        query = policy_query or DEFAULT_POLICY_QUERY_BY_RISK.get(
            prediction["risk_level"], "academic risk advisor guidance"
        )
        policy_results = self.policy_store.search(query, top_k=top_k_policies)

        return {
            **prediction,
            "high_risk_alert": compute_alert(prediction["risk_level"]),
            "policy_context": policy_results,
            "policy_query_used": query,
            "human_oversight_notice": HUMAN_OVERSIGHT_NOTICE,
        }

    def query_policies(self, query: str, top_k: int = 3) -> dict:
        """Direct policy/guideline lookup, independent of any prediction."""
        results = self.policy_store.search(query, top_k=top_k)
        return {
            "query": query,
            "results": results,
            "found": len(results) > 0,
            "note": (None if results else
                     "The provided policy/guideline documents do not contain "
                     "information relevant to this query."),
        }
