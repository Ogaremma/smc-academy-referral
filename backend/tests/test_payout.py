import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token
from app.db.models import PayoutDetails, User
from tests.conftest import create_telegram_init_data


async def _authenticate(client: AsyncClient, telegram_id: int, username: str):
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


def _headers(affiliate: dict) -> dict:
    return {"Authorization": f"Bearer {affiliate['access_token']}"}


async def _admin_headers(db_session: AsyncSession) -> dict[str, str]:
    admin = User(telegram_id=809500, username="payout_admin", is_admin=True)
    db_session.add(admin)
    await db_session.commit()
    token = create_access_token({"sub": str(admin.id), "telegram_id": admin.telegram_id})
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_affiliate_creates_and_reads_their_own_payout(client: AsyncClient):
    affiliate = await _authenticate(client, 812001, "payout_alice")
    headers = _headers(affiliate)

    assert (await client.get("/api/v1/payout", headers=headers)).status_code == 404

    created = await client.put(
        "/api/v1/payout",
        headers=headers,
        json={
            "account_name": "Alice Affiliate",
            "bank_name": "Access Bank",
            "account_number": "0123456789",
        },
    )
    assert created.status_code == 200
    body = created.json()
    assert body["account_name"] == "Alice Affiliate"
    assert body["bank_name"] == "Access Bank"
    assert body["account_number"] == "0123456789"
    assert body["updated_at"]
    assert "id" not in body
    assert "user_id" not in body

    fetched = await client.get("/api/v1/payout", headers=headers)
    assert fetched.status_code == 200
    assert fetched.json() == body


@pytest.mark.asyncio
async def test_affiliate_updates_existing_payout_without_duplicating(
    client: AsyncClient, db_session: AsyncSession
):
    affiliate = await _authenticate(client, 812002, "payout_bob")
    headers = _headers(affiliate)

    await client.put(
        "/api/v1/payout",
        headers=headers,
        json={"account_name": "Bob", "bank_name": "GTBank", "account_number": "1111111111"},
    )
    updated = await client.put(
        "/api/v1/payout",
        headers=headers,
        json={"account_name": "Bob B", "bank_name": "Zenith", "account_number": "2222222222"},
    )
    assert updated.status_code == 200
    assert updated.json()["account_number"] == "2222222222"

    rows = (
        await db_session.execute(
            select(PayoutDetails).where(
                PayoutDetails.user_id == affiliate["user"]["id"]
            )
        )
    ).scalars().all()
    assert len(rows) == 1
    assert rows[0].bank_name == "Zenith"


@pytest.mark.asyncio
async def test_affiliate_only_sees_their_own_payout(client: AsyncClient):
    alice = await _authenticate(client, 812003, "payout_scoped_a")
    bob = await _authenticate(client, 812004, "payout_scoped_b")

    await client.put(
        "/api/v1/payout",
        headers=_headers(alice),
        json={"account_name": "Alice", "bank_name": "Bank A", "account_number": "0001"},
    )
    await client.put(
        "/api/v1/payout",
        headers=_headers(bob),
        json={"account_name": "Bob", "bank_name": "Bank B", "account_number": "0002"},
    )

    alice_view = (await client.get("/api/v1/payout", headers=_headers(alice))).json()
    bob_view = (await client.get("/api/v1/payout", headers=_headers(bob))).json()

    assert alice_view["account_name"] == "Alice"
    assert alice_view["account_number"] == "0001"
    assert bob_view["account_name"] == "Bob"
    assert bob_view["account_number"] == "0002"


@pytest.mark.asyncio
async def test_payout_requires_authentication(client: AsyncClient):
    assert (await client.get("/api/v1/payout")).status_code == 401
    assert (
        await client.put(
            "/api/v1/payout",
            json={"account_name": "A", "bank_name": "B", "account_number": "1234"},
        )
    ).status_code == 401


@pytest.mark.asyncio
async def test_payout_validation_rejects_blank_and_short_fields(client: AsyncClient):
    affiliate = await _authenticate(client, 812005, "payout_validation")
    headers = _headers(affiliate)

    blank = await client.put(
        "/api/v1/payout",
        headers=headers,
        json={"account_name": "   ", "bank_name": "Bank", "account_number": "1234"},
    )
    assert blank.status_code == 422

    short = await client.put(
        "/api/v1/payout",
        headers=headers,
        json={"account_name": "A", "bank_name": "Bank", "account_number": "12"},
    )
    assert short.status_code == 422


@pytest.mark.asyncio
async def test_admin_can_view_affiliate_payout_but_affiliates_cannot(
    client: AsyncClient, db_session: AsyncSession
):
    affiliate = await _authenticate(client, 812006, "payout_carol")
    await client.put(
        "/api/v1/payout",
        headers=_headers(affiliate),
        json={"account_name": "Carol", "bank_name": "UBA", "account_number": "9999999999"},
    )
    admin_headers = await _admin_headers(db_session)

    allowed = await client.get(
        f"/api/v1/admin/affiliates/{affiliate['user']['id']}/payout",
        headers=admin_headers,
    )
    assert allowed.status_code == 200
    assert allowed.json()["account_number"] == "9999999999"
    assert "user_id" not in allowed.json()

    denied = await client.get(
        f"/api/v1/admin/affiliates/{affiliate['user']['id']}/payout",
        headers=_headers(affiliate),
    )
    assert denied.status_code == 403


@pytest.mark.asyncio
async def test_admin_payout_view_returns_404_when_none_saved(
    client: AsyncClient, db_session: AsyncSession
):
    affiliate = await _authenticate(client, 812007, "payout_dave")
    admin_headers = await _admin_headers(db_session)
    response = await client.get(
        f"/api/v1/admin/affiliates/{affiliate['user']['id']}/payout",
        headers=admin_headers,
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_payout_details_do_not_leak_through_dashboard_endpoints(
    client: AsyncClient,
):
    affiliate = await _authenticate(client, 812008, "payout_erin")
    headers = _headers(affiliate)
    await client.put(
        "/api/v1/payout",
        headers=headers,
        json={"account_name": "Erin", "bank_name": "Keystone", "account_number": "7777777777"},
    )

    for path in ("/api/v1/user/dashboard", "/api/v1/user/me", "/api/v1/referrals"):
        response = await client.get(path, headers=headers)
        assert response.status_code == 200
        assert "7777777777" not in response.text
        assert "Keystone" not in response.text
