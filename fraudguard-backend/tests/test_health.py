"""Integration tests for GET /health (Step 8)."""


def test_health_returns_ok(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200

    body = response.json()
    assert body["status"] in {"healthy", "unhealthy"}
    assert set(body["checks"].keys()) == {"database", "redis", "model"}

    # The test DB is real and reachable by construction (see conftest), and
    # the trained model artifacts ship committed in the repo — so a correctly
    # configured test environment should always report both as available.
    assert body["checks"]["database"] == "up"
    assert body["checks"]["model"] == "loaded"
