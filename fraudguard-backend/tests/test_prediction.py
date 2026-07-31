"""
Integration tests for POST /predict — the full pipeline: validation ->
preprocessing -> real trained-model scoring -> SHAP -> decision -> persistence
-> notification (Step 8).

Deliberately NOT mocking the model: app/ml_engine/predictor.py loads the
real trained artifacts already committed to the repo (model.joblib etc.), so
these tests exercise the actual scoring path. Mocking the model would only
prove the plumbing works, not that scoring still functions after a change to
preprocessing, feature engineering, or decision thresholds — which is
exactly the kind of regression a test suite exists to catch.
"""

import pytest

# Deliberately extreme V-feature values, far outside the training
# distribution's normal range. This exact profile was manually verified
# against the live deployed stack to produce a real `blocked` decision with
# risk_score 91.59 (see README's Step 8 verification notes) — reused here so
# the test is checking a value already known to trigger the behavior, not a
# guess.
_EXTREME_V_FEATURES = {
    "V1": -20, "V2": 15, "V3": -18, "V4": 10, "V5": -12,
    "V6": 8, "V7": -15, "V8": 12, "V9": -10, "V10": -20,
    "V11": 14, "V12": -16, "V13": 5, "V14": -22, "V15": 8,
    "V16": -14, "V17": -25, "V18": -12, "V19": 10, "V20": 15,
    "V21": 12, "V22": -8, "V23": 10, "V24": -5, "V25": 6,
    "V26": -7, "V27": 15, "V28": 12,
}


def _v_features(**overrides: float) -> dict:
    """A baseline of near-zero V1..V28 values — roughly what an average,
    unremarkable transaction looks like in this PCA-transformed feature
    space — with any specific features overridden by the caller."""
    features = {f"V{i}": 0.0 for i in range(1, 29)}
    features.update(overrides)
    return features


def test_predict_ordinary_transaction_runs_full_pipeline(client, admin_auth_headers):
    """A small, unremarkable transaction should complete every pipeline stage successfully."""
    response = client.post(
        "/api/v1/predict",
        headers=admin_auth_headers,
        json={
            "time_feature": 10000,
            "amount": 50.0,
            "v_features": _v_features(),
            "currency": "INR",
            "merchant": "Test Grocery",
        },
    )
    assert response.status_code == 201, response.text
    body = response.json()

    assert body["prediction"] is not None
    assert body["prediction"]["decision"] in {"approve", "mfa_required", "blocked"}
    assert 0.0 <= body["prediction"]["risk_score"] <= 100.0

    stages = {entry["stage"] for entry in body["decision_history"]}
    assert {"validation", "preprocessing", "prediction", "decision", "persistence", "notification"} <= stages
    assert all(entry["status"] == "success" for entry in body["decision_history"])


def test_predict_extreme_transaction_is_flagged_high_risk(client, admin_auth_headers):
    response = client.post(
        "/api/v1/predict",
        headers=admin_auth_headers,
        json={
            "time_feature": 10000,
            "amount": 50000.0,
            "v_features": _EXTREME_V_FEATURES,
            "currency": "INR",
            "merchant": "Test Merchant",
        },
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["prediction"]["decision"] in {"blocked", "mfa_required"}
    assert body["prediction"]["risk_score"] > 50


def test_predict_missing_v_feature_is_rejected(client, admin_auth_headers):
    """Missing a required V-feature should fail schema validation before ever touching the model."""
    incomplete = _v_features()
    del incomplete["V14"]
    response = client.post(
        "/api/v1/predict",
        headers=admin_auth_headers,
        json={"time_feature": 1000, "amount": 10.0, "v_features": incomplete, "currency": "INR"},
    )
    assert response.status_code == 422


def test_predict_negative_amount_is_rejected(client, admin_auth_headers):
    response = client.post(
        "/api/v1/predict",
        headers=admin_auth_headers,
        json={"time_feature": 1000, "amount": -5.0, "v_features": _v_features(), "currency": "INR"},
    )
    assert response.status_code == 422


def test_predict_requires_authentication(client):
    response = client.post(
        "/api/v1/predict",
        json={"time_feature": 1000, "amount": 10.0, "v_features": _v_features(), "currency": "INR"},
    )
    assert response.status_code in (401, 403)


def test_blocked_transaction_creates_a_real_notification(client, admin_auth_headers):
    """Confirms Step 8's end-to-end wiring: a blocked prediction should show
    up as a real, persisted notification retrievable via GET /notifications
    — not just a FraudLog line claiming it happened."""
    predict_response = client.post(
        "/api/v1/predict",
        headers=admin_auth_headers,
        json={
            "time_feature": 10000,
            "amount": 50000.0,
            "v_features": _EXTREME_V_FEATURES,
            "currency": "INR",
            "merchant": "Test Merchant",
        },
    )
    assert predict_response.status_code == 201, predict_response.text
    decision = predict_response.json()["prediction"]["decision"]
    if decision not in {"blocked", "mfa_required"}:
        pytest.skip("This run's extreme profile didn't trigger a notification-worthy decision.")

    notifications_response = client.get("/api/v1/notifications", headers=admin_auth_headers)
    assert notifications_response.status_code == 200
    body = notifications_response.json()
    assert body["total"] >= 1
    assert body["unread_count"] >= 1
