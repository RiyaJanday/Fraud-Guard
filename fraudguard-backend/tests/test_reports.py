"""Integration tests for GET /reports/* (Step 9)."""


def test_summary_pdf_downloads_successfully(client, admin_auth_headers):
    response = client.get("/api/v1/reports/summary.pdf", headers=admin_auth_headers)
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert "attachment" in response.headers["content-disposition"]
    # A real PDF always starts with this magic header — cheap sanity check
    # that reportlab actually produced a valid file, not an empty/broken one.
    assert response.content.startswith(b"%PDF")


def test_transactions_csv_downloads_successfully(client, admin_auth_headers):
    response = client.get("/api/v1/reports/transactions.csv", headers=admin_auth_headers)
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert "attachment" in response.headers["content-disposition"]

    # Header row should always be present, even with zero transactions —
    # an empty file (not even a header) would mean the endpoint silently
    # failed rather than correctly reporting "no rows".
    body_text = response.content.decode("utf-8")
    assert "Transaction ID" in body_text.splitlines()[0]


def test_reports_reject_invalid_date_range(client, admin_auth_headers):
    """date_from after date_to should be a clean validation error, not a
    silently-empty or nonsensical report."""
    response = client.get(
        "/api/v1/reports/transactions.csv",
        headers=admin_auth_headers,
        params={"date_from": "2026-12-31T00:00:00Z", "date_to": "2026-01-01T00:00:00Z"},
    )
    assert response.status_code == 422


def test_reports_require_authentication(client):
    response = client.get("/api/v1/reports/summary.pdf")
    assert response.status_code in (401, 403)
