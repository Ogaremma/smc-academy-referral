"""Contract test for the Form-bound Apps Script onFormSubmit payload.

The Apps Script builds the webhook body from the submitted form response and
posts it when the submission carries a referral code. This test replays that
exact envelope - including the complete answer list - and asserts the whole
chain: one referral, full answers preserved, correct affiliate attribution, a
referral count of exactly one, and no duplicate on a repeated delivery.
"""
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Referral, WebhookLog
from tests.conftest import TEST_WEBHOOK_SECRET, create_telegram_init_data

PROOF_URL = "https://drive.google.com/file/d/onform-proof/view"

ANSWERS = [
    {"question": "Full Name", "answer": "Grace Ade"},
    {"question": "Email Address", "answer": "grace@example.com"},
    {"question": "Telegram Username", "answer": "@graceade"},
    {"question": "Course", "answer": "Forex Trading"},
    {"question": "Payment Amount", "answer": "50000"},
    {"question": "Payment Screenshot", "answer": PROOF_URL},
]


async def _affiliate(client: AsyncClient, telegram_id: int, username: str) -> dict:
    response = await client.post(
        "/api/v1/auth/telegram",
        json={
            "init_data": create_telegram_init_data(
                user_dict={"id": telegram_id, "username": username}
            )
        },
    )
    assert response.status_code == 200
    return response.json()


def _on_form_submit_payload(code: str, response_id: str) -> dict:
    """Mirror the body the Apps Script buildPayload posts for a submission."""
    return {
        "response_id": response_id,
        "submitted_at": "2026-09-23T09:15:00.000Z",
        "referral_code": code,
        "candidate_email": "grace@example.com",
        "candidate_telegram_handle": "@graceade",
        "answers": ANSWERS,
    }


async def _deliver(client: AsyncClient, payload: dict) -> dict:
    response = await client.post(
        "/api/v1/webhooks/google-form",
        headers={"X-Webhook-Secret": TEST_WEBHOOK_SECRET},
        json=payload,
    )
    assert response.status_code == 200, response.text
    return response.json()


@pytest.mark.asyncio
async def test_on_form_submit_credits_one_referral_with_the_full_submission(
    client: AsyncClient, db_session: AsyncSession
):
    affiliate = await _affiliate(client, 850001, "on_form_affiliate")
    payload = _on_form_submit_payload(affiliate["referral_code"], "onform-submit-1")

    first = await _deliver(client, payload)
    assert first["success"] is True

    referral = (
        await db_session.execute(
            select(Referral).where(
                Referral.google_form_response_id == "onform-submit-1"
            )
        )
    ).scalar_one()
    assert referral.referrer_id == affiliate["user"]["id"]
    assert referral.status == "verified"
    assert referral.candidate_email == "grace@example.com"
    assert referral.candidate_telegram_handle == "@graceade"

    log = (
        await db_session.execute(
            select(WebhookLog).where(
                WebhookLog.google_form_response_id == "onform-submit-1",
                WebhookLog.status == "processed",
            )
        )
    ).scalar_one()
    for answer in ANSWERS:
        assert answer["answer"] in log.raw_payload

    dashboard = await client.get(
        "/api/v1/user/dashboard",
        headers={"Authorization": f"Bearer {affiliate['access_token']}"},
    )
    assert dashboard.status_code == 200
    assert dashboard.json()["total_verified_referrals"] == 1

    second = await _deliver(client, payload)
    assert second["referral_id"] == first["referral_id"]
    rows = (
        await db_session.execute(
            select(Referral).where(
                Referral.google_form_response_id == "onform-submit-1"
            )
        )
    ).scalars().all()
    assert len(rows) == 1
