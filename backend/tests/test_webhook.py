import pytest
from datetime import datetime, timezone
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Referral, WebhookLog
from tests.conftest import TEST_WEBHOOK_SECRET, create_telegram_init_data


@pytest.mark.asyncio
async def test_webhook_query_param_secret_is_not_accepted(client: AsyncClient):
    payload = {
        "response_id": "gform_resp_query_param_test",
        "referral_code": "SMC-INVALID999",
        "candidate_email": "candidate@example.com",
        "submitted_at": "2026-08-30T10:00:00Z",
    }

    response = await client.post(
        f"/api/v1/webhooks/google-form?secret={TEST_WEBHOOK_SECRET}",
        json=payload,
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_webhook_invalid_secret(client: AsyncClient):
    """Test 9: Invalid webhook secret is rejected with 401 Unauthorized."""
    payload = {
        "response_id": "gform_resp_001",
        "referral_code": "SMC-TEST01",
        "candidate_email": "candidate@example.com",
        "submitted_at": "2026-08-30T10:00:00Z",
    }

    response = await client.post(
        "/api/v1/webhooks/google-form",
        headers={"X-Webhook-Secret": "WRONG_SECRET_KEY"},
        json=payload,
    )

    assert response.status_code == 401
    assert "Unauthorized" in response.json()["detail"]


@pytest.mark.asyncio
async def test_webhook_missing_secret(client: AsyncClient):
    payload = {
        "response_id": "gform_resp_missing_secret",
        "referral_code": "SMC-TEST01",
        "submitted_at": "2026-08-30T10:00:00Z",
    }

    response = await client.post("/api/v1/webhooks/google-form", json=payload)

    assert response.status_code == 401
    assert "Unauthorized" in response.json()["detail"]


@pytest.mark.asyncio
async def test_webhook_invalid_referral_code(client: AsyncClient, db_session: AsyncSession):
    """Test 11: Webhook payload with nonexistent referral code is safely rejected and logged."""
    payload = {
        "response_id": "gform_resp_nonexistent",
        "referral_code": "SMC-INVALID999",
        "candidate_email": "candidate@example.com",
        "submitted_at": "2026-08-30T10:00:00Z",
    }

    response = await client.post(
        "/api/v1/webhooks/google-form",
        headers={"X-Webhook-Secret": TEST_WEBHOOK_SECRET},
        json=payload,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is False
    assert "Invalid or inactive referral code" in data["message"]
    assert data["referral_id"] is None

    # Verify log entry in WebhookLog table
    stmt = select(WebhookLog).where(WebhookLog.google_form_response_id == "gform_resp_nonexistent")
    res = await db_session.execute(stmt)
    log = res.scalar_one_or_none()
    assert log is not None
    assert log.status == "invalid_code"


@pytest.mark.asyncio
async def test_successful_referral_and_idempotency(client: AsyncClient, db_session: AsyncSession):
    """
    Test 8, Test 10, Test 12:
    1. Authenticate user to get referral code.
    2. Submit valid webhook -> Referral created with status='verified'.
    3. Submit duplicate webhook with same response_id -> Idempotent response, referral count remains 1.
    4. Fetch user dashboard -> verified count is 1.
    """
    # 1. Register referrer user
    init_data = create_telegram_init_data(user_dict={"id": 555666777, "username": "referrer_john"})
    auth_res = await client.post("/api/v1/auth/telegram", json={"init_data": init_data})
    assert auth_res.status_code == 200
    auth_data = auth_res.json()
    token = auth_data["access_token"]
    ref_code = auth_data["referral_code"]

    # 2. First Webhook Submission (Successful)
    payload_1 = {
        "response_id": "gform_resp_unique_101",
        "referral_code": ref_code,
        "candidate_email": "student1@smcacademy.org",
        "candidate_telegram_handle": "@candidate1",
        "submitted_at": "2026-08-29T14:35:12+01:00",
    }

    wh_res_1 = await client.post(
        "/api/v1/webhooks/google-form",
        headers={"X-Webhook-Secret": TEST_WEBHOOK_SECRET},
        json=payload_1,
    )

    assert wh_res_1.status_code == 200
    wh_data_1 = wh_res_1.json()
    assert wh_data_1["success"] is True
    assert wh_data_1["referral_id"] is not None
    referral_id_1 = wh_data_1["referral_id"]

    # Verify Referral record in DB
    stmt_ref = select(Referral).where(Referral.id == referral_id_1)
    referral_db = (await db_session.execute(stmt_ref)).scalar_one_or_none()
    assert referral_db is not None
    assert referral_db.google_form_response_id == "gform_resp_unique_101"
    assert referral_db.status == "verified"
    assert referral_db.candidate_email == "student1@smcacademy.org"
    assert referral_db.referrer_id == auth_data["user"]["id"]
    expected_submitted_at = datetime(2026, 8, 29, 13, 35, 12, tzinfo=timezone.utc)
    actual_submitted_at = referral_db.registered_at
    if actual_submitted_at.tzinfo is None:
        actual_submitted_at = actual_submitted_at.replace(tzinfo=timezone.utc)
    assert actual_submitted_at == expected_submitted_at

    # 3. Duplicate Webhook Submission (Idempotency check)
    wh_res_2 = await client.post(
        "/api/v1/webhooks/google-form",
        headers={"X-Webhook-Secret": TEST_WEBHOOK_SECRET},
        json=payload_1,
    )

    assert wh_res_2.status_code == 200
    wh_data_2 = wh_res_2.json()
    assert wh_data_2["success"] is True
    assert "Duplicate response ID" in wh_data_2["message"]
    assert wh_data_2["referral_id"] == referral_id_1  # Returns same referral ID without creating another

    # Ensure only 1 Referral record exists for this response_id
    stmt_count = select(Referral).where(Referral.google_form_response_id == "gform_resp_unique_101")
    all_refs = (await db_session.execute(stmt_count)).scalars().all()
    assert len(all_refs) == 1

    # 4. Check User Dashboard Count
    dash_res = await client.get(
        "/api/v1/user/dashboard",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert dash_res.status_code == 200
    dash_data = dash_res.json()

    # Verified referral count must be exactly 1
    assert dash_data["total_verified_referrals"] == 1
    assert len(dash_data["recent_verified_activity"]) == 1
    activity = dash_data["recent_verified_activity"][0]
    assert "candidate_email" not in activity
    assert "candidate_telegram_handle" not in activity
