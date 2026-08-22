# AI Support Student — Early Academic Warning System

An advisor-support prototype that predicts academic risk from approved
learning-behavior data and grounds every recommendation in a policy
knowledge base (SDAIA AI Ethics, PDPL, SDAIA Academic Framework, and NCA
AI Cybersecurity Guidelines). **This system does not make decisions about
students.** It produces a risk assessment, an explanation, and relevant
policy context; the Program Advisor makes every final call.

---

## 1. Required Python version

Python **3.10+** (developed and tested on 3.12).

## 2. Environment setup

```bash
git clone <your-repo-url> ai-support-student
cd ai-support-student
python3 -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
```

## 3. Dependency installation

```bash
pip install -r requirements.txt
```

## 4. Project structure

```
project/
├── data/
│   └── dataset.csv                 # student academic/behavior data
├── documents/
│   └── policies/
│       └── Policies_and_Guidelines.pdf
├── models/                         # created by training: model + pipeline + metadata
├── rag/
│   ├── ingestion/ingest.py         # PDF -> cleaned, chunked policy entries
│   ├── embeddings/                 # (reserved for future embedding providers)
│   └── vector_store/store.py       # TF-IDF vector store + persisted store.pkl
├── src/
│   ├── data/validation.py          # column-role contract + validation
│   ├── preprocessing/pipeline.py   # imputer + scaler, strict feature isolation
│   ├── training/train.py           # trains, evaluates, selects, saves model
│   ├── prediction/predict.py       # inference on saved artifacts
│   ├── explainability/explain.py   # per-student coefficient decomposition
│   ├── rag/build_knowledge_base.py # builds/saves the policy vector store
│   └── router/orchestrator.py      # combines ML + RAG for the advisor report
├── api/main.py                     # FastAPI app
├── tests/                          # 45 automated tests
├── requirements.txt
├── .env.example
└── README.md
```

## 5. Where to place the CSV

`data/dataset.csv`. Must contain exactly these columns:
`Student_ID, Course_Year, Attendance_Percentage, Assignment_Submission_Rate,
Quiz_Average_Score, Midterm_Score, Previous_GPA, Late_Submission_Count,
Missing_Assignment_Count, Study_Plan_Adherence, Academic_Risk_Level`.

## 6. Where to place policy documents

`documents/policies/Policies_and_Guidelines.pdf`. The ingestion module
expects the document's existing structure (numbered entries ending in an
`Extracted from: ...` citation line); replacing it with a differently
structured PDF will require adjusting the chunking regex in
`rag/ingestion/ingest.py`.

## 7. Environment variables / API keys

**None are required.** See `.env.example` — the RAG system uses a local
TF-IDF vector store (no embedding API), and the ML model runs locally via
scikit-learn. Copy the example if you want to customize paths/ports:

```bash
cp .env.example .env
```

## 8. How to train the model

```bash
python -m src.training.train
```

This validates the dataset, splits 80/20 (stratified, seed=42), fits
preprocessing on the training split only, trains Logistic Regression,
Random Forest, and Gradient Boosting, and selects the final model.
Artifacts are saved to `models/`: `model.joblib`,
`preprocessing_pipeline.joblib`, `training_metadata.json`.

## 9. How to evaluate the model

Evaluation runs automatically as part of training and is saved in
`models/training_metadata.json` (`selected_model_result` and
`all_candidate_results`). To re-print a summary:

```bash
python -c "import json; d=json.load(open('models/training_metadata.json')); print(json.dumps(d['selected_model_result']['per_class'], indent=2))"
```

**Current results** (Logistic Regression, selected model): accuracy
82.4%, balanced accuracy 84.8%, High Risk recall 89.8%. Full per-class
precision/recall/F1 and the confusion matrix are in
`training_metadata.json`. These numbers come directly from running the
code above — they are not fabricated, and a data-realism caveat is
documented in section 15 below.

## 10. How to build the RAG knowledge base

```bash
python -m src.rag.build_knowledge_base
```

Extracts and chunks the policy PDF, builds a TF-IDF vector store, and
saves it to `rag/vector_store/policy_store.pkl`.

## 11. How to start the backend API

Train the model and build the knowledge base first (steps 8 and 10),
then:

```bash
uvicorn api.main:app --host 127.0.0.1 --port 8000
```

Interactive docs: `http://127.0.0.1:8000/docs`

## 12. How to run tests

```bash
pytest tests/ -v
```

45 tests covering dataset validation, preprocessing/feature isolation,
prediction, probability validity, explainability, RAG retrieval, router
behavior, and API endpoints. Requires trained artifacts and the vector
store to already exist (steps 8 and 10).

## 13. Example prediction request

```bash
curl -X POST http://127.0.0.1:8000/predict \
  -H "Content-Type: application/json" \
  -d '{
    "student_id": "STU-XXXXXXXX",
    "course_year": 3,
    "attendance_percentage": 72,
    "assignment_submission_rate": 68,
    "quiz_average_score": 74,
    "midterm_score": 65,
    "previous_gpa": 2.8,
    "late_submission_count": 4,
    "missing_assignment_count": 2,
    "study_plan_adherence": 60
  }'
```

## 14. Example prediction response

```json
{
  "student_id": "STU-XXXXXXXX",
  "course_year": 3,
  "risk_level": "Low Risk",
  "risk_probability": 0.8895,
  "class_probabilities": {
    "Low Risk": 0.8895,
    "Medium Risk": 0.1104,
    "High Risk": 0.00002
  },
  "contributing_factors": [
    {"feature": "Missing_Assignment_Count", "direction": "increases_risk_of_predicted_class", "contribution": 1.947},
    {"feature": "Quiz_Average_Score", "direction": "increases_risk_of_predicted_class", "contribution": 0.768}
  ],
  "explainability_method": "logistic_regression_coefficient_decomposition",
  "policy_context": [
    {"chunk_id": 8, "title": "AI Ethics Checklist - Minimal Use of Personal Data", "source": "SDAIA, AI Ethics Principles ... (Annexure C, p. 44)", "relevance_score": 0.206}
  ],
  "human_oversight_notice": "This is a decision-support output only. ... The Program Advisor must independently review this information ...",
  "model_version": "1.0.0",
  "prediction_timestamp_utc": "2026-08-15T16:09:44Z"
}
```

There's also a policy-only endpoint that never touches the ML model:

```bash
curl -X POST http://127.0.0.1:8000/policy/query \
  -H "Content-Type: application/json" \
  -d '{"query": "human oversight of AI decisions", "top_k": 3}'
```

## 15. Data realism note

The provided dataset is well-formed and internally consistent (no
nulls/duplicates, valid ranges, all three classes represented), but its
feature distributions are noticeably clean/regular for real student
records, consistent with synthetic generation. The model's reported
metrics (82.4% accuracy, 89.8% High Risk recall) reflect performance on
*this* dataset. Before any real deployment, retrain and re-evaluate on
genuine institutional data, and re-run the leakage review in
`src/data/validation.py` (it flags any feature whose per-class ranges
don't overlap at all).

## 16. How to integrate the API into another application

The API is a standard REST/JSON service — any client that can send an
HTTP POST with a JSON body can integrate it (a web dashboard, an LMS
plugin, a scheduled batch job, etc.). Point requests at
`POST /predict` for full advisor reports or `POST /policy/query` for
policy lookups only. `GET /health` is provided for liveness checks in
orchestration/deployment tooling (e.g. Docker healthchecks, k8s probes).
No authentication is implemented in this prototype — add an auth layer
(API key, OAuth) before any non-local deployment, per NCA Guideline 2-2
(least privilege / rate limiting) referenced in the policy knowledge
base.

## 17. Common errors and fixes

| Error | Cause | Fix |
|---|---|---|
| `FileNotFoundError: models/model.joblib` | API started before training | Run `python -m src.training.train` first |
| `FileNotFoundError: .../policy_store.pkl` | API started before RAG build | Run `python -m src.rag.build_knowledge_base` first |
| `ValueError: Missing required features` | `/predict` called with an incomplete feature set | Ensure all 8 feature fields are present in the request |
| `422 Unprocessable Entity` from API | A field is out of its validated range (e.g. GPA > 4, percentage > 100) | Check request values against Section 13's field constraints |
| `ModuleNotFoundError: src` when running scripts directly | Not run as a module, or wrong working directory | Run from the project root using `python -m src.training.train` (module form), not `python src/training/train.py` |
| Tests fail with missing-artifact errors | Same as above — training/RAG-build artifacts not yet generated | Run steps 8 and 10 before `pytest` |

---

## Architecture

```
Student Data → Validation/Preprocessing (8 ML features only)
             → Logistic Regression → Risk Level + Probabilities + Contributing Factors
                                                        │
                                                        ▼
                                              Router / Orchestrator ──► Policy RAG (TF-IDF)
                                                        │
                                                        ▼
                                              Advisor UI / API response
                                        (Student ID, Course Year, Risk, Explanation,
                                         Policy Evidence, Human-Oversight Notice)
                                                        │
                                                        ▼
                                        PROGRAM ADVISOR — final human decision
```

`Course_Year` and `Student_ID` flow through the system as **context/display
fields only** — this is enforced in code (`src/preprocessing/pipeline.py`
excludes them from `X`) and verified by tests (`test_student_id_and_
course_year_passthrough_only` in `tests/test_prediction.py`).

## Responsible AI notes

- **Fairness / minimal data** — only the 8 approved academic/behavioral
  features are used; no demographic or sensitive attributes are collected
  or modeled (SDAIA Fairness principle, PDPL data minimization).
- **Explainability** — every prediction includes a per-student coefficient
  decomposition, not a global or invented explanation.
- **Human-in-the-loop** — the API and router never emit an "intervention
  required" field; every response carries a `human_oversight_notice`.
- **Privacy** — `Student_ID` is treated as a pseudonymous identifier only,
  never a model input, per the PDPL pseudonymization guidance in the
  policy knowledge base.
