import pytest
from sqlalchemy import select
from app.db.models import User
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
