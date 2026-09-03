import pytest
from httpx import AsyncClient
from urllib.parse import parse_qs, urlparse

from tests.conftest import create_telegram_init_data


@pytest.mark.asyncio
async def test_user_me_endpoint(client: AsyncClient):
    """Test /api/v1/user/me endpoint with valid JWT."""
    init_data = create_telegram_init_data(user_dict={"id": 777888999, "username": "alice"})
    auth_res = await client.post("/api/v1/auth/telegram", json={"init_data": init_data})
    token = auth_res.json()["access_token"]
    expected_code = auth_res.json()["referral_code"]

    res = await client.get(
        "/api/v1/user/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert res.status_code == 200
    data = res.json()
    assert data["user"]["telegram_id"] == 777888999
    assert data["referral_code"] == expected_code


@pytest.mark.asyncio
async def test_public_referral_redirect(client: AsyncClient):
    """Test public referral redirection endpoint /r/{code}."""
    init_data = create_telegram_init_data(user_dict={"id": 123123123, "username": "bob"})
    auth_res = await client.post("/api/v1/auth/telegram", json={"init_data": init_data})
    ref_code = auth_res.json()["referral_code"]

    res = await client.get(f"/r/{ref_code}", follow_redirects=False)

    assert res.status_code == 307
    assert "location" in res.headers
    location = res.headers["location"]
    assert "docs.google.com/forms" in location
    assert parse_qs(urlparse(location).query)["entry.1398965380"] == [ref_code]


@pytest.mark.asyncio
async def test_invalid_public_referral_code_returns_404(client: AsyncClient):
    res = await client.get("/r/SMC-NOTREAL", follow_redirects=False)
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_dashboard_link_uses_backend_google_form_redirect(client: AsyncClient):
    init_data = create_telegram_init_data(user_dict={"id": 333444555, "username": "carol"})
    auth_res = await client.post("/api/v1/auth/telegram", json={"init_data": init_data})
    token = auth_res.json()["access_token"]
    ref_code = auth_res.json()["referral_code"]

    res = await client.get(
        "/api/v1/user/dashboard",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert res.status_code == 200
    assert res.json()["personal_referral_link"] == f"http://localhost:8000/r/{ref_code}"


@pytest.mark.asyncio
async def test_multiple_form_submissions_increase_referrer_count(client: AsyncClient):
    init_data = create_telegram_init_data(user_dict={"id": 444555666, "username": "referrer"})
    auth_res = await client.post("/api/v1/auth/telegram", json={"init_data": init_data})
    assert auth_res.status_code == 200
    auth_data = auth_res.json()
    token = auth_data["access_token"]
    code = auth_data["referral_code"]

    for index in range(3):
        response = await client.post(
            "/api/v1/webhooks/google-form",
            headers={"X-Webhook-Secret": "test_super_secret_webhook_key_123"},
            json={
                "response_id": f"multiple-form-response-{index}",
                "referral_code": code,
                "submitted_at": "2026-09-01T12:00:00Z",
            },
        )
        assert response.status_code == 200
        assert response.json()["success"] is True

    duplicate = await client.post(
        "/api/v1/webhooks/google-form",
        headers={"X-Webhook-Secret": "test_super_secret_webhook_key_123"},
        json={
            "response_id": "multiple-form-response-1",
            "referral_code": code,
            "submitted_at": "2026-09-01T12:00:00Z",
        },
    )
    assert duplicate.json()["success"] is True

    dashboard = await client.get(
        "/api/v1/user/dashboard",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert dashboard.json()["total_verified_referrals"] == 3
