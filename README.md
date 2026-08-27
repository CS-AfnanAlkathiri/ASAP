# ASAP — AI Support for Academic Progress
### An Early Academic Warning System for Program Advisors

Built by **Team EduVision AI** for the **ITU AI Readiness Hackathon**.

---

## Overview

ASAP is an advisor-support prototype that predicts academic risk from approved
learning-behavior indicators and grounds every recommendation in a policy
knowledge base.

**This system does not make decisions about students.** It produces a risk assessment, an explanation, and relevant policy context — the Program Advisor makes every final call.

## Live Demo

🔗 **ASAP** [Try The Demo](https://asap-7avk.onrender.com)

> This is a hackathon MVP demonstrating the advisor-facing workflow, including academic risk prediction, contributing factors, policy retrieval, and human-in-the-loop review.

## Team

| Name | Role | Email |
|------|------|-----|
| _Afnan Alkathiri_ | Full-Stack Developer, Documentation & Report | afnanalkathiri21@gmail.com |
| _Rowaida Bamarhool_ | Full-Stack Developer, Documentation & Report | rowaidabam@gmail.com |
| _Abdallah Eyad_ | Documentation, Demo & Report | abdullaheyad44@gmail.com |

## Policy Knowledge Base

The RAG layer is grounded in official Saudi policy and guidance documents,
primarily issued by **SDAIA — the Saudi Data and Artificial Intelligence
Authority**, the national body responsible for data and AI governance,
strategy, and regulation in Saudi Arabia. The knowledge base also includes
guidance co-issued with the **Saudi Ministry of Education** and cybersecurity
guidelines from the **National Cybersecurity Authority (NCA)**. Together they
cover:

- AI ethics and risk classification
- Personal data protection (PDPL)
- Academic/education-sector AI qualifications and standards
- Generative AI use in general education
- AI cybersecurity guidelines

Every policy-based response in the system cites its source document and page
number rather than paraphrasing without attribution.

## How It Works

1. **Prediction** — A Logistic Regression model (selected over Random Forest
   and Gradient Boosting) classifies students into Low / Medium / High risk
   using 8 approved academic and learning-behavior features.
2. **Explainability** — Per-student contributing factors are computed directly
   from the model's coefficients — a real explanation, not a heuristic.
3. **Alerting** — A configurable rule flags High Risk cases for advisor review.
4. **Policy grounding (RAG)** — A local TF-IDF knowledge base retrieves
   relevant policy guidance, with source and page citations, for every
   prediction.
5. **Human oversight** — Every API response includes an explicit
   human-oversight notice. The advisor decides intervention, referral, or no
   action.

## Results

- **82.4%** accuracy, **84.8%** balanced accuracy, **89.8%** High Risk recall
  (80/20 stratified test split, seed=42)
- 51 automated tests covering validation, preprocessing, prediction,
  explainability, alerting, RAG retrieval, routing, and API endpoints

## Architecture

The ML pipeline follows **ITU-T Y.3172** as an architectural reference:

```
SRC → C → PP → M → P → D → SINK
```

Source data → Collection → Preprocessing (feature isolation) → Model
(Logistic Regression) → Policy layer (RAG + alerting) → Distribution (API) →
Advisor.

Project alignment with **ITU AI Readiness 1.0/2.0** is documented in `/report`.

## Repository Structure

```
├── api/            # FastAPI application (predict, policy/query, health)
├── data/            # Dataset
├── documents/       # Source policy PDF(s)
├── models/          # Trained model, preprocessing pipeline, metadata
├── rag/              # Policy retrieval (TF-IDF vector store)
├── src/               # Core pipeline: validation, preprocessing, training,
│                        prediction, explainability, alerting, routing
└── tests/            # Automated test suite

```

## Tech Stack

- **ML:** scikit-learn (Logistic Regression, Random Forest, Gradient Boosting)
- **API:** FastAPI
- **RAG:** local TF-IDF vector store (no external embedding API required)
- **Testing:** pytest

## Important Caveat

The dataset used is internally clean and consistent, but its feature
distributions are more regular than typical real institutional data,
consistent with synthetic generation. Results should be read as prototype
evidence — real deployment would require retraining and evaluation on
governed institutional data.
