"""Integration tests for registration, login, and session endpoints."""


def test_first_registered_user_becomes_admin(client):
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "first@example.com", "password": "Password123", "full_name": "First User"},
    )
    assert response.status_code == 201, response.text
    assert response.json()["role"] == "admin"


def test_second_registered_user_is_not_admin(client):
    client.post(
        "/api/v1/auth/register",
        json={"email": "first@example.com", "password": "Password123", "full_name": "First User"},
    )
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "second@example.com", "password": "Password123", "full_name": "Second User"},
    )
    assert response.status_code == 201, response.text
    assert response.json()["role"] == "analyst"


def test_self_registering_as_admin_is_rejected_after_bootstrap(client):
    client.post(
        "/api/v1/auth/register",
        json={"email": "first@example.com", "password": "Password123", "full_name": "First User"},
    )
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "wannabe-admin@example.com",
            "password": "Password123",
            "full_name": "Wannabe Admin",
            "role": "admin",
        },
    )
    assert response.status_code == 403, response.text


def test_duplicate_email_registration_rejected(client):
    payload = {"email": "dupe@example.com", "password": "Password123", "full_name": "Dupe"}
    first = client.post("/api/v1/auth/register", json=payload)
    assert first.status_code == 201
    second = client.post("/api/v1/auth/register", json=payload)
    assert second.status_code == 409, second.text


def test_weak_password_rejected(client):
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "weak@example.com", "password": "alllettersnodigits", "full_name": "Weak"},
    )
    assert response.status_code == 422


def test_login_with_wrong_password_rejected(client):
    client.post(
        "/api/v1/auth/register",
        json={"email": "user@example.com", "password": "Password123", "full_name": "User"},
    )
    response = client.post("/api/v1/auth/login", json={"email": "user@example.com", "password": "WrongPass1"})
    assert response.status_code == 401


def test_login_with_unknown_email_rejected(client):
    response = client.post("/api/v1/auth/login", json={"email": "nobody@example.com", "password": "Password123"})
    assert response.status_code == 401


def test_me_endpoint_returns_current_user(client, admin_auth_headers):
    response = client.get("/api/v1/auth/me", headers=admin_auth_headers)
    assert response.status_code == 200
    assert "email" in response.json()
    assert response.json()["role"] == "admin"


def test_me_endpoint_requires_authentication(client):
    response = client.get("/api/v1/auth/me")
    assert response.status_code in (401, 403)
