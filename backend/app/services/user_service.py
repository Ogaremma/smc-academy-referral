from typing import Any, Dict, Tuple
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.security import generate_referral_code
from app.db.models import ReferralCode, User


async def generate_unique_referral_code_for_user(
    db: AsyncSession, user_id: int
) -> ReferralCode:
    """Generate a unique referral code for a user with collision retries."""
    for _ in range(10):
        code_str = generate_referral_code()
        stmt = select(ReferralCode).where(ReferralCode.code == code_str)
        result = await db.execute(stmt)
        if result.scalar_one_or_none() is None:
            ref_code = ReferralCode(user_id=user_id, code=code_str, is_active=True)
            db.add(ref_code)
            await db.flush()
            return ref_code
    raise RuntimeError("Failed to generate a unique referral code after multiple attempts.")


async def get_user_by_telegram_id(
    db: AsyncSession, telegram_id: int
) -> Tuple[User, ReferralCode]:
    """Retrieve user and associated referral code by Telegram ID."""
    stmt = (
        select(User)
        .options(selectinload(User.referral_code))
        .where(User.telegram_id == telegram_id)
    )
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    if user:
        return user, user.referral_code
    return None, None


async def get_or_create_telegram_user(
    db: AsyncSession, telegram_user_data: Dict[str, Any]
) -> Tuple[User, ReferralCode]:
    """
    Find existing Telegram user or create a new user with a unique referral code.
    Updates basic profile information if changed.
    """
    telegram_id = telegram_user_data.get("id")
    if not telegram_id:
        raise ValueError("Telegram user data missing required 'id' field.")

    stmt = (
        select(User)
        .options(selectinload(User.referral_code))
        .where(User.telegram_id == int(telegram_id))
    )
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    username = telegram_user_data.get("username")
    first_name = telegram_user_data.get("first_name")
    last_name = telegram_user_data.get("last_name")
    photo_url = telegram_user_data.get("photo_url")

    if user:
        # Update user profile fields if needed
        updated = False
        if user.username != username:
            user.username = username
            updated = True
        if user.first_name != first_name:
            user.first_name = first_name
            updated = True
        if user.last_name != last_name:
            user.last_name = last_name
            updated = True
        if user.photo_url != photo_url:
            user.photo_url = photo_url
            updated = True

        if updated:
            db.add(user)

        # Ensure user has a referral code
        if not user.referral_code:
            referral_code = await generate_unique_referral_code_for_user(db, user.id)
        else:
            referral_code = user.referral_code

        await db.commit()
        await db.refresh(user)
        return user, referral_code
    else:
        # Create new user
        new_user = User(
            telegram_id=int(telegram_id),
            username=username,
            first_name=first_name,
            last_name=last_name,
            photo_url=photo_url,
            is_active=True,
        )
        db.add(new_user)
        await db.flush()  # Assigns new_user.id

        referral_code = await generate_unique_referral_code_for_user(db, new_user.id)
        await db.commit()
        await db.refresh(new_user)
        return new_user, referral_code
