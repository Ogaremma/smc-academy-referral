import pytest
from sqlalchemy import select
from app.core.security import create_access_token
from app.db.models import AuditLog, ReferralCode, User
from tests.conftest import create_telegram_init_data

@pytest.mark.asyncio
async def test_normal_affiliate_cannot_access_admin(client):
    response = await client.post("/api/v1/auth/telegram", json={"init_data": create_telegram_init_data(user_dict={"id": 88001, "username": "affiliate"})})
    token = response.json()["access_token"]
    denied = await client.get("/api/v1/admin/affiliates", headers={"Authorization": f"Bearer {token}"})
    assert denied.status_code == 403

@pytest.mark.asyncio
async def test_initial_admin_is_bound_by_telegram_id(client, db_session):
    response = await client.post("/api/v1/auth/telegram", json={"init_data": create_telegram_init_data(user_dict={"id": 88002, "username": "Web3Launcherr"})})
    assert response.status_code == 200
    user = (await db_session.execute(select(User).where(User.telegram_id == 88002))).scalar_one()
    assert user.is_admin and user.is_protected_admin


@pytest.mark.asyncio
async def test_affiliates_directory_contains_only_current_affiliates(client, db_session):
    admin = User(telegram_id=88100, username="admin", is_admin=True)
    current = User(
        telegram_id=88101,
        username="Web3Launcherr",
        first_name="Web3",
        last_name="Launcher",
        account_status="ACTIVE",
    )
    registered_without_link = User(
        telegram_id=88102,
        username="registered",
        first_name="Registered",
        account_status="ACTIVE",
    )
    revoked = User(
        telegram_id=88103,
        username="revoked",
        first_name="Revoked",
        account_status="REVOKED",
    )
    inactive_code_user = User(
        telegram_id=88104,
        username="inactive_code",
        account_status="ACTIVE",
    )
    deleted_a = User(
        telegram_id=-88105,
        deleted_telegram_id=88101,
        username="Web3Launcherr",
        is_active=False,
        account_status="ACTIVE",
    )
    deleted_b = User(
        telegram_id=-88106,
        deleted_telegram_id=88101,
        username="Web3Launcherr",
        is_active=False,
        account_status="ACTIVE",
    )
    db_session.add_all(
        [admin, current, registered_without_link, revoked, inactive_code_user, deleted_a, deleted_b]
    )
    await db_session.flush()
    db_session.add_all(
        [
            ReferralCode(user_id=current.id, code="CURRENT", is_active=True),
            ReferralCode(user_id=revoked.id, code="REVOKED", is_active=True),
            ReferralCode(user_id=inactive_code_user.id, code="INACTIVE", is_active=False),
            ReferralCode(user_id=deleted_a.id, code="OLDA", is_active=False),
            ReferralCode(user_id=deleted_b.id, code="OLDB", is_active=False),
        ]
    )
    await db_session.commit()
    token = create_access_token({"sub": str(admin.id), "telegram_id": admin.telegram_id})

    response = await client.get(
        "/api/v1/admin/affiliates",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    affiliates = response.json()
    returned_ids = {affiliate["id"] for affiliate in affiliates}
    assert returned_ids == {current.id, revoked.id}
    current_row = next(affiliate for affiliate in affiliates if affiliate["id"] == current.id)
    assert current_row["username"] == "Web3Launcherr"
    assert current_row["first_name"] == "Web3"
    assert current_row["last_name"] == "Launcher"
    assert current_row["referral_code"] == "CURRENT"
    assert current_row["referral_count"] == 0
    historical = (
        await db_session.execute(select(User).where(User.deleted_telegram_id == 88101))
    ).scalars().all()
    assert len(historical) == 2
    assert all(user.is_active is False for user in historical)


@pytest.mark.asyncio
async def test_revoke_and_restore_preserve_current_affiliate_lifecycle(client, db_session):
    admin = User(telegram_id=88200, username="admin", is_admin=True)
    affiliate = User(telegram_id=88201, username="affiliate", first_name="Affiliate")
    db_session.add_all([admin, affiliate])
    await db_session.flush()
    referral_code = ReferralCode(user_id=affiliate.id, code="LIFECYCLE", is_active=True)
    db_session.add(referral_code)
    await db_session.commit()
    token = create_access_token({"sub": str(admin.id), "telegram_id": admin.telegram_id})
    headers = {"Authorization": f"Bearer {token}"}

    revoked = await client.post(
        f"/api/v1/admin/affiliates/{affiliate.id}/revoke", headers=headers
    )
    assert revoked.status_code == 200
    await db_session.refresh(affiliate)
    await db_session.refresh(referral_code)
    assert affiliate.account_status == "REVOKED"
    assert affiliate.is_active is True
    assert referral_code.is_active is True

    directory = await client.get("/api/v1/admin/affiliates", headers=headers)
    assert {row["id"] for row in directory.json()} == {affiliate.id}

    restored = await client.post(
        f"/api/v1/admin/affiliates/{affiliate.id}/restore", headers=headers
    )
    assert restored.status_code == 200
    await db_session.refresh(affiliate)
    await db_session.refresh(referral_code)
    assert affiliate.account_status == "ACTIVE"
    assert affiliate.is_active is True
    assert referral_code.code == "LIFECYCLE"
    assert referral_code.is_active is True
    actions = (
        await db_session.execute(
            select(AuditLog.action).where(AuditLog.target_user_id == affiliate.id)
        )
    ).scalars().all()
    assert set(actions) == {"affiliate_revoked", "affiliate_restored"}


@pytest.mark.asyncio
async def test_deleted_lifecycle_cannot_be_restored(client, db_session):
    admin = User(telegram_id=88300, username="admin", is_admin=True)
    deleted = User(
        telegram_id=-88301,
        deleted_telegram_id=88301,
        is_active=False,
        account_status="ACTIVE",
    )
    db_session.add_all([admin, deleted])
    await db_session.commit()
    token = create_access_token({"sub": str(admin.id), "telegram_id": admin.telegram_id})

    response = await client.post(
        f"/api/v1/admin/affiliates/{deleted.id}/restore",
        headers={"Authorization": f"Bearer {token}"},
    )
    revoke_response = await client.post(
        f"/api/v1/admin/affiliates/{deleted.id}/revoke",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 400
    assert revoke_response.status_code == 400
    await db_session.refresh(deleted)
    assert deleted.is_active is False


@pytest.mark.asyncio
async def test_protected_admin_cannot_be_removed_or_demoted(client, db_session):
    admin = User(telegram_id=88400, username="admin", is_admin=True)
    protected = User(
        telegram_id=88401,
        username="Web3Launcherr",
        is_admin=True,
        is_protected_admin=True,
    )
    db_session.add_all([admin, protected])
    await db_session.commit()
    token = create_access_token({"sub": str(admin.id), "telegram_id": admin.telegram_id})
    headers = {"Authorization": f"Bearer {token}"}

    removed = await client.delete(
        f"/api/v1/admin/administrators/{protected.id}", headers=headers
    )
    demoted = await client.post(
        f"/api/v1/admin/administrators/{protected.id}/demote", headers=headers
    )

    assert removed.status_code == 403
    assert demoted.status_code == 403
    await db_session.refresh(protected)
    assert protected.is_admin is True
    assert protected.is_protected_admin is True
