"""The Apps Script configuration check used during production verification."""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import extract_referral_code, is_referral_code
from tests.conftest import TEST_WEBHOOK_SECRET, create_telegram_init_data

DIAGNOSTICS_URL = "/api/v1/webhooks/google-form/diagnostics"


def test_referral_code_extraction_ignores_unrelated_text():
    """The backend hostname must never be read as a referral code."""
    host = "https://smc-academy-referral.onrender.com"
    assert is_referral_code(extract_referral_code(host)) is False
    assert is_referral_code(extract_referral_code("A friend")) is False
    assert is_referral_code(extract_referral_code("")) is False
    assert extract_referral_code(f"{host}/r/SMC-7FELG5") == "SMC-7FELG5"
    assert extract_referral_code(f"{host}?entry.1=SMC-7FELG5") == "SMC-7FELG5"
    assert extract_referral_code("my code is smc-7felg5") == "SMC-7FELG5"
    assert is_referral_code("SMC-7FELG5") is True
    assert is_referral_code("https://example.com/r/SMC-7FELG5") is False


@pytest.mark.asyncio
async def test_diagnostics_requires_the_webhook_secret(client: AsyncClient):
    assert (await client.post(DIAGNOSTICS_URL, json={})).status_code == 401
    wrong = await client.post(
        DIAGNOSTICS_URL, headers={"X-Webhook-Secret": "nope"}, json={}
    )
    assert wrong.status_code == 401


@pytest.mark.asyncio
async def test_diagnostics_reports_configuration_and_code_owner(
    client: AsyncClient, db_session: AsyncSession
):
    affiliate = await client.post(
        "/api/v1/auth/telegram",
        json={
            "init_data": create_telegram_init_data(
                user_dict={"id": 940001, "username": "diagnostics_affiliate"}
            )
        },
    )
    assert affiliate.status_code == 200
    code = affiliate.json()["referral_code"]

    response = await client.post(
        DIAGNOSTICS_URL,
        headers={"X-Webhook-Secret": TEST_WEBHOOK_SECRET},
        json={"referral_code": f"https://example.com/r/{code}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["webhook_secret_configured"] is True
    assert payload["webhook_url"].endswith("/api/v1/webhooks/google-form")
    assert payload["counts"]["affiliates"] >= 1
    assert payload["referral_code"]["resolved"] == code
    assert payload["referral_code"]["exists"] is True
    assert payload["referral_code"]["is_active"] is True
    assert payload["referral_code"]["affiliate"]["username"] == "diagnostics_affiliate"
    assert payload["prefill_url"] is not None
    assert code in payload["prefill_url"]


@pytest.mark.asyncio
async def test_diagnostics_reports_unknown_codes(
    client: AsyncClient, db_session: AsyncSession
):
    response = await client.post(
        DIAGNOSTICS_URL,
        headers={"X-Webhook-Secret": TEST_WEBHOOK_SECRET},
        json={"referral_code": "SMC-NOPE99"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["referral_code"]["exists"] is False
    assert "does not exist" in payload["referral_code"]["reason"]
    assert payload["webhook_log_statuses"] == {}
