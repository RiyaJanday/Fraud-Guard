"""
Integration tests for /model/status and /model/retrain.

Deliberately does NOT call POST /model/retrain as an admin: Starlette's
TestClient runs FastAPI BackgroundTasks synchronously within the request
before returning a response (unlike a real ASGI server, where it's
genuinely deferred), so an admin-authenticated call here would block the
test suite on a real training run against creditcard.csv. The 403-for-
non-admin path is safe to test because the permission check fails before
the endpoint body — and therefore the background task — ever runs.
"""


def test_model_status_requires_authentication(client):
    response = client.get("/api/v1/model/status")
    assert response.status_code in (401, 403)


def test_model_status_returns_active_model_and_training_state(client, admin_auth_headers):
    response = client.get("/api/v1/model/status", headers=admin_auth_headers)
    assert response.status_code == 200, response.text
    body = response.json()

    assert "training_in_progress" in body
    assert body["training_in_progress"] is False

    # The trained artifacts ship committed in the repo, but registering them
    # in THIS test database isn't guaranteed (that only happens via
    # train_model.py or register_production_model.py against a real DB), so
    # active_model may legitimately be null here — just assert the shape is
    # correct when it IS present.
    if body["active_model"] is not None:
        for field in ("version", "algorithm", "accuracy", "precision", "recall", "f1_score", "roc_auc", "pr_auc"):
            assert field in body["active_model"]


def test_retrain_requires_admin_role(client, analyst_auth_headers):
    """Analyst (non-admin) must be rejected before the background task ever runs."""
    response = client.post("/api/v1/model/retrain", headers=analyst_auth_headers)
    assert response.status_code == 403


def test_retrain_requires_authentication(client):
    response = client.post("/api/v1/model/retrain")
    assert response.status_code in (401, 403)
