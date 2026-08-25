<div align="center">

🛡️ FraudGuard

Real-Time AI-Powered Credit Card Fraud Detection & Monitoring Platform

Detect → Explain → Decide → Review → Learn

FraudGuard is an end-to-end fraud detection platform that combines machine learning, business rules, SHAP explainability, real-time monitoring, analyst review workflows, and analytics into one modern dashboard.

<br/>











<br/>

⭐ Star this repository · 📖 Documentation · 🚀 Deployment

</div>

🚨 Why FraudGuard?

Traditional fraud detection often stops at:

"This transaction looks suspicious."

FraudGuard goes further.

It answers:

Why was the transaction considered risky?

Which business rule was triggered?

What did the ML model predict?

Should the transaction be approved, flagged, or blocked?

Does a human analyst need to review it?

What happened after the decision?

The result is an explainable, operational fraud detection workflow rather than a black-box prediction API.

✨ What Makes It Different?

Capability

FraudGuard

🤖 ML-based fraud prediction ✅

🧠 SHAP explanations ✅

📏 Business-rule engine ✅

🚫 Rule-based decision override ✅

⚡ Real-time WebSocket monitoring ✅

🔎 Transaction investigation ✅

👩‍💻 Analyst review queue ✅

🔐 JWT authentication & RBAC ✅

📊 Fraud analytics & dashboards ✅

📉 Data drift monitoring ✅

📄 CSV/PDF reports ✅

🧾 Audit trail ✅

🧠 Model registry & version history ✅

🏗️ System Architecture

flowchart LR
    A[💳 Transaction] --> B[⚙️ Feature Engineering]
    B --> C[🤖 ML Fraud Model]

    C --> D[📈 Risk Score]
    C --> E[🔬 SHAP Explainability]

    D --> F[📏 Business Rules Engine]
    F --> G{Final Decision}

    G -->|Approve| H[✅ Approved]
    G -->|Flag| I[⚠️ Review Queue]
    G -->|Block| J[🚫 Blocked]

    J --> I
    I --> K[👩‍💻 Analyst Review]
    K --> L[📝 Resolution + Audit Trail]

    G --> M[⚡ WebSocket]
    M --> N[📡 Live Monitoring]

    G --> O[📊 Dashboard]
    G --> P[🔔 Notifications]

Decision Philosophy

FraudGuard does not blindly trust the ML model.

For example:

Transaction Amount = ₹75,000

                 ML MODEL
                    ↓
           Fraud Probability
              0.0525%
                    ↓
              Risk Score 0.05
                    ↓
                APPROVE
                    │
                    ▼
          BUSINESS RULE ENGINE
                    │
        ┌───────────┴───────────┐
        ↓                       ↓
 Amount > ₹50,000          Amount > ₹20,000
        ↓                       ↓
      BLOCK                    FLAG
        └───────────┬───────────┘
                    ↓
              🚫 BLOCKED
                    ↓
             REVIEW QUEUE

This allows deterministic business policies to override a low-risk ML prediction when required.

🚀 Core Features

🤖 1. AI Fraud Detection

Transactions are processed through a machine-learning inference pipeline to generate:

Fraud probability

Risk score

Confidence

Final decision

Model version

Inference latency

The platform currently supports an XGBoost-based fraud detection workflow and maintains model/version information through the Model Registry.

🔬 2. Explainable AI with SHAP

Fraud detection should not be a black box.

FraudGuard generates transaction-level SHAP explanations showing the strongest contributing features.

Example:

Top contributing signals

1. Hour
2. Amount_log
3. Amount
4. V1
5. V18

Each explanation can include:

Feature name

Human-readable label

Feature value

SHAP impact

Natural-language explanation

This makes model decisions easier for analysts to investigate.

📏 3. Business Rules Engine

Machine learning is only one part of fraud prevention.

FraudGuard also evaluates deterministic business rules such as:

IF amount > 50000
THEN BLOCK

or:

IF amount > 20000
THEN FLAG

Multiple rules can trigger for the same transaction.

The final decision is determined after combining the ML result with the active business rules.

⚡ 4. Real-Time Live Monitoring

Transactions can be streamed to the dashboard using WebSockets.

The Live Monitoring interface provides:

Real-time transaction feed

Merchant

Amount

Risk indicator

Approved/Blocked status

Stream controls

No manual refresh is required for the live stream.

🕵️ 5. Analyst Review Queue

Automatically blocked/high-risk transactions can enter an analyst workflow.

BLOCKED TRANSACTION
        ↓
PENDING REVIEW
        ↓
CLAIM CASE
        ↓
INVESTIGATE
        ↓
SHAP + BUSINESS RULES
        ↓
┌───────────────┐
│ LEGITIMATE    │
│      OR       │
│ CONFIRM FRAUD │
└───────────────┘
        ↓
AUDIT TRAIL

This creates a human-in-the-loop fraud investigation workflow.

📊 6. Fraud Detection Dashboard

The dashboard provides operational visibility into the fraud pipeline.

Includes

Total transactions

Fraud detected

Fraud blocked

Detection accuracy

Average risk score

Transaction volume

Fraud distribution

Risk trend

Model performance

Live risk gauge

Fraud heatmap

Recent alerts

Notifications

📉 7. Drift Monitoring

Fraud patterns change over time.

FraudGuard compares live transaction behavior against a reference distribution to identify potential data drift.

This helps answer:

"Is the incoming transaction population starting to look different from the data the model learned from?"

🧠 8. Model Registry

The Model Registry provides visibility into:

Active model

Algorithm

Accuracy

Precision

Recall

F1 score

ROC-AUC

PR-AUC

Training timestamp

Historical model versions

This creates a foundation for reproducible model operations and future retraining.

🔐 9. Authentication & Role-Based Access

FraudGuard includes:

JWT authentication

Admin role

Analyst role

Protected routes

Password reset flow

Role-based access control

🧾 10. Audit Trail

Fraud investigations need accountability.

FraudGuard records important review actions and case resolutions so that decisions can be traced later.

📄 11. Reports

Export operational data in:

CSV

PDF

Useful for analysis, reporting and demonstrations.

🖥️ Dashboard Preview

Add your screenshots to a docs/screenshots/ folder and uncomment the images below.

docs/
└── screenshots/
    ├── dashboard.png
    ├── transactions.png
    ├── live-monitoring.png
    ├── review-queue.png
    ├── model-registry.png
    └── business-rules.png

Overview

<!-- ![FraudGuard Dashboard](docs/screenshots/dashboard.png) -->

Live Monitoring

<!-- ![Live Monitoring](docs/screenshots/live-monitoring.png) -->

Transactions

<!-- ![Transactions](docs/screenshots/transactions.png) -->

Review Queue

<!-- ![Review Queue](docs/screenshots/review-queue.png) -->

Model Registry

<!-- ![Model Registry](docs/screenshots/model-registry.png) -->

🧰 Tech Stack

Backend

Technology

Purpose

Python

Core backend & ML ecosystem

FastAPI

REST API

SQLAlchemy

ORM / database access

Alembic

Database migrations

PostgreSQL

Persistent database

Redis

Caching / supporting infrastructure

XGBoost

Fraud classification

scikit-learn

ML preprocessing & evaluation

SHAP

Model explainability

WebSockets

Real-time updates

JWT

Authentication

Frontend

Technology

Purpose

React 19

UI

Vite

Development/build tooling

Tailwind CSS

Styling

Chart.js

Analytics visualizations

React Hook Form

Form management

Zod

Validation

Axios

API communication

Infrastructure

Docker
├── PostgreSQL
├── Redis
└── FastAPI backend

React/Vite frontend
        ↓
     REST API
        +
   WebSockets

📁 Project Structure

Fraud-Guard/
│
├── fraudguard-backend/
│   └── app/
│       ├── api/
│       │   └── v1/
│       │       ├── auth/
│       │       ├── transactions/
│       │       ├── analytics/
│       │       ├── drift/
│       │       └── ...
│       │
│       ├── core/
│       │   ├── config/
│       │   ├── security/
│       │   └── logging/
│       │
│       ├── ml_engine/
│       │   ├── model training
│       │   ├── inference
│       │   ├── SHAP explainer
│       │   └── drift detection
│       │
│       ├── models/
│       ├── repositories/
│       ├── schemas/
│       └── services/
│
├── fraudguard-frontend/
│   └── src/
│       ├── components/
│       ├── context/
│       ├── lib/
│       └── pages/
│
├── docker-compose.yml
├── seed_transactions.py
├── creditcard.csv
├── LOCAL_RUN.md
├── DEPLOYMENT.md
├── LICENSE
└── README.md

⚡ Quick Start

Prerequisites

Install:

Git

Docker Desktop

Node.js

Python 3.11

1️⃣ Clone

git clone https://github.com/RiyaJanday/Fraud-Guard.git
cd Fraud-Guard

2️⃣ Start backend infrastructure

docker compose up --build

Wait until the backend reports:

Application startup complete

Then open:

http://127.0.0.1:8000/docs

3️⃣ Start frontend

Open another terminal:

cd fraudguard-frontend
npm install
npm run dev

Open the Vite URL shown in the terminal, usually:

http://localhost:5173

4️⃣ Create an account

Register through the authentication flow.

The first registered account can be used as the administrator account according to the local setup flow.

🧪 Test the Fraud Pipeline

FraudGuard can be tested directly from Swagger.

Open:

http://127.0.0.1:8000/docs

Find:

POST /api/v1/predict

Example high-value transaction:

{
  "time_feature": 0,
  "amount": 75000,
  "currency": "INR",
  "merchant": "Test Merchant",
  "customer_reference": "TEST-CUSTOMER-001",
  "card_last4": "4242",
  "device_info": "Test Device",
  "ip_address": "127.0.0.1",
  "location": "Ahmedabad",
  "v_features": {
    "V1": 0.12,
    "V2": -0.31,
    "V3": 0.08,
    "V4": 0.22,
    "V5": -0.15,
    "V6": 0.41,
    "V7": -0.27,
    "V8": 0.13,
    "V9": -0.09,
    "V10": 0.35,
    "V11": -0.18,
    "V12": 0.06,
    "V13": 0.24,
    "V14": -0.12,
    "V15": 0.17,
    "V16": -0.21,
    "V17": 0.09,
    "V18": 0.14,
    "V19": -0.33,
    "V20": 0.19,
    "V21": -0.07,
    "V22": 0.28,
    "V23": -0.16,
    "V24": 0.11,
    "V25": 0.05,
    "V26": -0.23,
    "V27": 0.18,
    "V28": -0.04
  }
}

Expected decision flow

₹75,000
   ↓
ML model
   ↓
Low ML risk
   ↓
Business rules
   ↓
amount > 50,000
   ↓
🚫 BLOCKED
   ↓
Review Queue

This demonstrates one of FraudGuard's most important design principles:

The ML model provides intelligence; business rules provide deterministic control.

🔄 End-to-End Workflow

                  ┌───────────────┐
                  │   Transaction │
                  └───────┬───────┘
                          ↓
                  ┌───────────────┐
                  │ Validation    │
                  └───────┬───────┘
                          ↓
                  ┌───────────────┐
                  │ Preprocessing │
                  └───────┬───────┘
                          ↓
              ┌───────────────────────┐
              │     ML Prediction     │
              └───────────┬───────────┘
                          ↓
                Probability + Risk
                          ↓
              ┌───────────────────────┐
              │   Business Rules      │
              └───────────┬───────────┘
                          ↓
                  Final Decision
                          ↓
        ┌─────────────────┼─────────────────┐
        ↓                 ↓                 ↓
     APPROVE            FLAG              BLOCK
        │                 │                 │
        │                 └──────┬──────────┘
        │                        ↓
        │                 Review Queue
        │                        ↓
        │                 Analyst Review
        │                        ↓
        │                 Human Decision
        │                        ↓
        └───────────────→ Audit Trail

              ↘ WebSocket → Live Monitoring
              ↘ Analytics → Dashboard
              ↘ SHAP → Explainability
              ↘ Events → Notifications

📈 Model Evaluation

The Model Registry tracks standard classification metrics:

Accuracy
Precision
Recall
F1 Score
ROC-AUC
PR-AUC

Important: Accuracy alone is not sufficient for fraud detection because fraud datasets are typically imbalanced. Precision, recall, F1, ROC-AUC and PR-AUC are therefore tracked together.

🔐 Security

FraudGuard includes application-level security features such as:

JWT-based authentication

Role-based authorization

Protected API routes

Password reset flow

Audit logging

Input validation

Rate limiting

Environment-based configuration

⚠️ Production Note

Do not commit:

.env
database passwords
JWT secrets
API keys
private credentials

Use environment variables or a secret manager for production deployments.

☁️ Deployment

The project is designed around:

Frontend  → Vercel
Backend   → Render
Database  → PostgreSQL
Cache     → Redis

See DEPLOYMENT.md for the deployment workflow.

🗺️ Roadmap

ML fraud prediction

SHAP explainability

Business rules

Transaction monitoring

Real-time WebSocket feed

Analyst review queue

Dashboard analytics

Model registry

Drift monitoring

Audit trail

CSV/PDF reports

Automated model retraining pipeline

Advanced rule simulation

Champion/challenger model evaluation

Expanded production observability

Cloud deployment hardening

🎯 Project Goals

FraudGuard was designed around four principles:

1. Accuracy

Use machine learning to identify suspicious transaction patterns.

2. Explainability

Show analysts why a transaction received its risk score.

3. Control

Allow deterministic business policies to override model decisions.

4. Operations

Turn predictions into a complete monitoring and human-review workflow.

💡 Example Use Case

Imagine a customer makes a ₹75,000 first-time transaction.

The ML model may consider the transaction low risk.

But the organization's policy says:

Transactions above ₹50,000 from a first-time customer must be blocked for review.

FraudGuard handles this as:

ML says:
"Low risk"

Business Rules say:
"Policy violation"

FraudGuard says:
"BLOCK"

The analyst can then inspect:

transaction details

risk score

SHAP explanation

triggered business rules

decision history

and make the final human decision.

🏆 Why This Is More Than a Machine Learning Project

FraudGuard demonstrates the complete lifecycle of an applied ML system:

                DATA
                 ↓
           PREPROCESSING
                 ↓
          MODEL TRAINING
                 ↓
             INFERENCE
                 ↓
          EXPLAINABILITY
                 ↓
        BUSINESS DECISIONS
                 ↓
          HUMAN REVIEW
                 ↓
          AUDIT + REPORTING
                 ↓
        MONITORING + DRIFT
                 ↓
          FUTURE RETRAINING

It combines Machine Learning + Backend Engineering + Frontend Engineering + Databases + Real-Time Systems + Explainable AI + MLOps concepts in one application.

👩‍💻 Author

Riya Janday

B.Tech Computer Science Engineering — AI

Interested in:

🤖 Artificial Intelligence

🧠 Machine Learning

💻 Software Engineering

📊 Data & Analytics

🚀 Building production-oriented AI systems

<div align="center">

🛡️ FraudGuard

Don't just detect fraud. Understand it. Act on it. Learn from it.

<br/>

⭐ If you find this project interesting, consider starring the repository.

GitHub Repository

</div>
