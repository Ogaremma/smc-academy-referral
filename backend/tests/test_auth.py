import time
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import REFERRAL_CODE_ALPHABET, generate_referral_code
from app.db.models import ReferralCode, User
from app.services.user_service import get_or_create_telegram_user
from tests.conftest import TEST_BOT_TOKEN, create_telegram_init_data


@pytest.mark.asyncio
async def test_referral_code_format():
    """Test 4: Referral code generation format and alphabet exclusion."""
    code = generate_referral_code(prefix="SMC-", length=6)
    assert code.startswith("SMC-")
    assert len(code) == 10  # "SMC-" (4) + 6 chars
    random_part = code.replace("SMC-", "")
    for char in random_part:
        assert char in REFERRAL_CODE_ALPHABET
        assert char not in ["0", "O", "1", "I"]


@pytest.mark.asyncio
async def test_referral_code_uniqueness():
    """Test 5: Referral code uniqueness across multiple generations."""
    codes = set()
    for _ in range(100):
        code = generate_referral_code()
        assert code not in codes
        codes.add(code)


@pytest.mark.asyncio
async def test_telegram_init_data_valid(client: AsyncClient, db_session: AsyncSession):
    """Test 1 & Test 6: Valid Telegram initData authenticates user and creates user + referral code."""
    telegram_user = {
        "id": 1122334455,
        "first_name": "SMC",
        "last_name": "Trader",
        "username": "smctrader",
    }
    init_data_str = create_telegram_init_data(user_dict=telegram_user)

    response = await client.post(
        "/api/v1/auth/telegram",
        json={"init_data": init_data_str},
    )

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["telegram_id"] == 1122334455
    assert data["user"]["username"] == "smctrader"
    assert data["referral_code"].startswith("SMC-")

    # Verify database persistence
    stmt = select(User).where(User.telegram_id == 1122334455)
    res = await db_session.execute(stmt)
    user = res.scalar_one_or_none()
    assert user is not None
    assert user.first_name == "SMC"

    stmt_code = select(ReferralCode).where(ReferralCode.user_id == user.id)
    res_code = await db_session.execute(stmt_code)
    ref_code = res_code.scalar_one_or_none()
    assert ref_code is not None
    assert ref_code.code == data["referral_code"]


@pytest.mark.asyncio
async def test_invalid_telegram_hash(client: AsyncClient):
    """Test 2: Tampered Telegram hash is rejected with 401 Unauthorized."""
    init_data_str = create_telegram_init_data(tamper_hash=True)

    response = await client.post(
        "/api/v1/auth/telegram",
        json={"init_data": init_data_str},
    )

    assert response.status_code == 401
    assert "Invalid Telegram authentication signature" in response.json()["detail"]


@pytest.mark.asyncio
async def test_expired_telegram_auth_data(client: AsyncClient):
    """Test 3: Expired auth_date parameter is rejected."""
    two_days_ago = int(time.time()) - (48 * 3600)
    init_data_str = create_telegram_init_data(auth_date=two_days_ago)

    response = await client.post(
        "/api/v1/auth/telegram",
        json={"init_data": init_data_str},
    )

    assert response.status_code == 401
    assert "expired" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_duplicate_user_handling(client: AsyncClient, db_session: AsyncSession):
    """Test 7: Authenticating twice with same Telegram ID reuses user without creating duplicates."""
    telegram_user = {"id": 999888777, "username": "original_name"}
    init_data_1 = create_telegram_init_data(user_dict=telegram_user)

    res1 = await client.post("/api/v1/auth/telegram", json={"init_data": init_data_1})
    assert res1.status_code == 200
    code1 = res1.json()["referral_code"]

    # Authenticate second time with updated username
    telegram_user_updated = {"id": 999888777, "username": "updated_name"}
    init_data_2 = create_telegram_init_data(user_dict=telegram_user_updated)

    res2 = await client.post("/api/v1/auth/telegram", json={"init_data": init_data_2})
    assert res2.status_code == 200
    code2 = res2.json()["referral_code"]

    # Must retain same referral code
    assert code1 == code2
    assert res2.json()["user"]["username"] == "updated_name"

    # Ensure only 1 User record exists in DB
    stmt = select(User).where(User.telegram_id == 999888777)
    users = (await db_session.execute(stmt)).scalars().all()
    assert len(users) == 1


@pytest.mark.asyncio
async def test_existing_user_returns_loaded_referral_code(db_session: AsyncSession):
    telegram_id = 777666555

    _, created_code = await get_or_create_telegram_user(
        db_session,
        {"id": telegram_id, "username": "original_name"},
    )
    original_code = created_code.code

    user, existing_code = await get_or_create_telegram_user(
        db_session,
        {"id": telegram_id, "username": "updated_name"},
    )

    assert existing_code.code == original_code
    assert user.referral_code.code == original_code
