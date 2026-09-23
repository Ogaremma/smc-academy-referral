"""Telegram identity persistence and display-data tests.

The dashboards render an affiliate/admin identity from the stored Telegram
profile: ``@username`` first, then the Telegram name, and only then
``Telegram <id>``. These tests cover the persistence that feeds that order.
"""
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token
from app.db.models import User
from tests.conftest import create_telegram_init_data

PROFILE = {
    "id": 6261204018,
    "first_name": "Ogar",
    "last_name": "Emma",
    "username": "Web3Launcherr",
    "photo_url": "https://t.me/i/userpic/320/example.svg",
}


async def _login(client: AsyncClient, user: dict, create_account: bool):
    return await client.post(
        "/api/v1/auth/telegram",
        json={
            "init_data": create_telegram_init_data(user_dict=user),
            "create_account": create_account,
        },
    )


@pytest.mark.asyncio
async def test_returning_user_profile_is_refreshed_on_login(
    client: AsyncClient, db_session: AsyncSession
):
    """An account created before the profile was persisted gets its identity."""
    user = User(telegram_id=6261204018, is_active=True, account_status="ACTIVE")
    db_session.add(user)
    await db_session.commit()
    assert user.username is None and user.first_name is None

    response = await _login(client, PROFILE, create_account=False)

    assert response.status_code == 200
    payload = response.json()["user"]
    assert payload["username"] == "Web3Launcherr"
    assert payload["first_name"] == "Ogar"
    assert payload["last_name"] == "Emma"
    assert payload["photo_url"] == PROFILE["photo_url"]
    assert payload["telegram_id"] == 6261204018


@pytest.mark.asyncio
async def test_profile_fields_telegram_omits_are_preserved(
    client: AsyncClient, db_session: AsyncSession
):
    """A launch without photo access must not erase the stored identity."""
    await _login(client, PROFILE, create_account=True)

    without_photo = {
        "id": 6261204018,
        "first_name": "Ogar",
        "last_name": "Emma",
        "username": "Web3Launcherr",
    }
    response = await _login(client, without_photo, create_account=False)

    assert response.status_code == 200
    assert response.json()["user"]["photo_url"] == PROFILE["photo_url"]


@pytest.mark.asyncio
async def test_affiliate_registration_persists_the_signed_profile(
    client: AsyncClient, db_session: AsyncSession
):
    """A brand new affiliate is stored with the identity Telegram signed."""
    pending = await _login(client, PROFILE, create_account=False)
    assert pending.status_code == 200
    assert pending.json()["user"] is None

    registered = await client.post(
        "/api/v1/auth/affiliate/register",
        headers={"Authorization": f"Bearer {pending.json()['access_token']}"},
    )

    assert registered.status_code == 200
    stored = (
        await db_session.execute(select(User).where(User.telegram_id == 6261204018))
    ).scalar_one()
    assert stored.username == "Web3Launcherr"
    assert stored.first_name == "Ogar"
    assert stored.last_name == "Emma"
    assert stored.photo_url == PROFILE["photo_url"]


@pytest.mark.asyncio
async def test_pending_session_cannot_be_used_as_an_authenticated_session(
    client: AsyncClient,
):
    """The onboarding token must fail cleanly instead of erroring."""
    pending = await _login(client, PROFILE, create_account=False)
    token = pending.json()["access_token"]

    response = await client.get(
        "/api/v1/user/me", headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_identity_data_is_available_to_the_admin_dashboards(
    client: AsyncClient, db_session: AsyncSession
):
    """Admin payloads expose the fields the identity formatter needs."""
    await _login(client, PROFILE, create_account=True)
    account = (
        await db_session.execute(select(User).where(User.telegram_id == 6261204018))
    ).scalar_one()

    admin = User(telegram_id=6261204040, username="ops_admin", is_admin=True)
    db_session.add(admin)
    await db_session.commit()
    headers = {
        "Authorization": f"Bearer {create_access_token({'sub': str(admin.id), 'telegram_id': admin.telegram_id})}"
    }

    affiliates = (await client.get("/api/v1/admin/affiliates", headers=headers)).json()
    entry = next(row for row in affiliates if row["id"] == account.id)
    assert entry["username"] == "Web3Launcherr"
    assert entry["first_name"] == "Ogar"
    assert entry["last_name"] == "Emma"

    detail = (
        await client.get(f"/api/v1/admin/affiliates/{account.id}", headers=headers)
    ).json()
    assert detail["username"] == "Web3Launcherr"
    assert detail["first_name"] == "Ogar"


@pytest.mark.asyncio
async def test_account_without_telegram_profile_keeps_the_id_fallback(
    client: AsyncClient, db_session: AsyncSession
):
    """No invented identity: the numeric id is the last resort."""
    user = User(telegram_id=6000000001, is_active=True, account_status="ACTIVE")
    db_session.add(user)
    await db_session.commit()

    response = await _login(
        client, {"id": 6000000001}, create_account=False
    )

    assert response.status_code == 200
    payload = response.json()["user"]
    assert payload["username"] is None
    assert payload["first_name"] is None
    assert payload["telegram_id"] == 6000000001
