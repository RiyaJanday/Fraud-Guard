"""Integration tests for GET /drift (Step 7)."""


def test_drift_reports_insufficient_data_with_no_transactions(client, admin_auth_headers):
    """With a freshly-wiped test DB (see conftest's db_session fixture), zero
    transactions exist yet — the endpoint must refuse to compute a
    statistically meaningless verdict rather than guessing one."""
    response = client.get("/api/v1/drift?sample_size=30", headers=admin_auth_headers)
    assert response.status_code == 200, response.text

    body = response.json()
    assert body["status"] == "insufficient_data"
    assert body["sample_size"] == 0
    assert body["drift_detected"] is False
    assert body["features"] == []


def test_drift_requires_authentication(client):
    response = client.get("/api/v1/drift?sample_size=30")
    assert response.status_code in (401, 403)


def test_drift_rejects_sample_size_below_minimum(client, admin_auth_headers):
    """sample_size has a `ge=30` constraint at the router level — below that,
    a KS test's result is too noisy to report responsibly (see drift_detector.py)."""
    response = client.get("/api/v1/drift?sample_size=5", headers=admin_auth_headers)
    assert response.status_code == 422
