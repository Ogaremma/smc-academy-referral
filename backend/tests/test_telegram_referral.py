import pytest
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ReferralCode, TelegramReferral, User
from tests.conftest import TEST_WEBHOOK_SECRET, create_telegram_init_data


async def authenticate(
    client: AsyncClient,
    telegram_id: int,
    username: str,
    signed_start_param: str | None = None,
    submitted_start_param: str | None = None,
):
    init_data = create_telegram_init_data(
        user_dict={"id": telegram_id, "username": username},
        start_param=signed_start_param,
    )
    return await client.post(
        "/api/v1/auth/telegram",
        json={
            "init_data": init_data,
            "start_param": submitted_start_param or signed_start_param,
        },
    )


@pytest.mark.asyncio
async def test_new_user_gets_telegram_referral(client: AsyncClient, db_session: AsyncSession):
    referrer_response = await authenticate(client, 10001, "referrer")
    referrer = referrer_response.json()

    referred_response = await authenticate(
        client,
        10002,
        "referred",
        signed_start_param=referrer["referral_code"],
    )
    assert referred_response.status_code == 200

    attribution = (
        await db_session.execute(select(TelegramReferral))
    ).scalar_one()
    assert attribution.referrer_user_id == referrer["user"]["id"]
    assert attribution.referred_user_id == referred_response.json()["user"]["id"]

    dashboard = await client.get(
        "/api/v1/user/dashboard",
        headers={"Authorization": f"Bearer {referred_response.json()['access_token']}"},
    )
    assert dashboard.json()["registration_form_url"].endswith(
        f"/r/{referrer['referral_code']}"
    )


@pytest.mark.asyncio
async def test_existing_referral_is_idempotent_and_cannot_be_overwritten(
    client: AsyncClient,
    db_session: AsyncSession,
):
    referrer_a = (await authenticate(client, 11001, "referrer_a")).json()
    referrer_c = (await authenticate(client, 11003, "referrer_c")).json()

    first = await authenticate(
        client, 11002, "referred", signed_start_param=referrer_a["referral_code"]
    )
    second = await authenticate(
        client, 11002, "referred", signed_start_param=referrer_a["referral_code"]
    )
    third = await authenticate(
        client, 11002, "referred", signed_start_param=referrer_c["referral_code"]
    )
    assert first.status_code == second.status_code == third.status_code == 200

    referred_user_id = first.json()["user"]["id"]
    attribution = (
        await db_session.execute(
            select(TelegramReferral).where(
                TelegramReferral.referred_user_id == referred_user_id
            )
        )
    ).scalar_one()
    assert attribution.referrer_user_id == referrer_a["user"]["id"]
    assert await db_session.scalar(
        select(func.count(TelegramReferral.id)).where(
            TelegramReferral.referred_user_id == referred_user_id
        )
    ) == 1
    assert await db_session.scalar(
        select(func.count(ReferralCode.id)).where(
            ReferralCode.user_id == referred_user_id
        )
    ) == 1


@pytest.mark.asyncio
async def test_self_and_invalid_referrals_are_ignored(
    client: AsyncClient,
    db_session: AsyncSession,
):
    user = (await authenticate(client, 12001, "self_referrer")).json()
    self_response = await authenticate(
        client, 12001, "self_referrer", signed_start_param=user["referral_code"]
    )
    invalid_response = await authenticate(
        client, 12002, "invalid_referral", signed_start_param="SMC-NOTREAL"
    )
    assert self_response.status_code == invalid_response.status_code == 200
    assert await db_session.scalar(select(func.count(TelegramReferral.id))) == 0


@pytest.mark.asyncio
async def test_unsigned_submitted_code_cannot_replace_signed_start_param(
    client: AsyncClient,
    db_session: AsyncSession,
):
    referrer_a = (await authenticate(client, 13001, "referrer_a")).json()
    referrer_c = (await authenticate(client, 13003, "referrer_c")).json()
    referred = await authenticate(
        client,
        13002,
        "referred",
        signed_start_param=referrer_a["referral_code"],
        submitted_start_param=referrer_c["referral_code"],
    )
    attribution = (
        await db_session.execute(
            select(TelegramReferral).where(
                TelegramReferral.referred_user_id == referred.json()["user"]["id"]
            )
        )
    ).scalar_one()
    assert attribution.referrer_user_id == referrer_a["user"]["id"]


@pytest.mark.asyncio
async def test_arbitrary_browser_telegram_id_is_ignored(client: AsyncClient):
    init_data = create_telegram_init_data(
        user_dict={"id": 13502, "username": "signed_identity"},
    )
    response = await client.post(
        "/api/v1/auth/telegram",
        json={"init_data": init_data, "telegram_id": 999999999},
    )
    assert response.status_code == 200
    assert response.json()["user"]["telegram_id"] == 13502


@pytest.mark.asyncio
async def test_google_form_code_cannot_overwrite_telegram_attribution(
    client: AsyncClient,
    db_session: AsyncSession,
):
    referrer_a = (await authenticate(client, 14001, "referrer_a")).json()
    referrer_c = (await authenticate(client, 14003, "referrer_c")).json()
    referred = await authenticate(
        client, 14002, "referred", signed_start_param=referrer_a["referral_code"]
    )

    webhook = await client.post(
        "/api/v1/webhooks/google-form",
        headers={"X-Webhook-Secret": TEST_WEBHOOK_SECRET},
        json={
            "response_id": "telegram-attribution-form-swap",
            "referral_code": referrer_c["referral_code"],
            "submitted_at": "2026-09-01T12:00:00Z",
        },
    )
    assert webhook.status_code == 200

    attribution = (
        await db_session.execute(
            select(TelegramReferral).where(
                TelegramReferral.referred_user_id == referred.json()["user"]["id"]
            )
        )
    ).scalar_one()
    assert attribution.referrer_user_id == referrer_a["user"]["id"]
