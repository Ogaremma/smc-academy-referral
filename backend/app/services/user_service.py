import asyncio
from typing import Any, Dict, Tuple
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import IntegrityError

from app.core.security import generate_referral_code
from app.db.models import ReferralCode, TelegramReferral, User


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
            try:
                async with db.begin_nested():
                    db.add(ref_code)
                    await db.flush()
                return ref_code
            except IntegrityError:
                continue
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


async def establish_telegram_referral(
    db: AsyncSession,
    referred_user_id: int,
    referral_code: str,
) -> TelegramReferral | None:
    """Create an immutable Telegram referral attribution when the code is valid."""
    existing_result = await db.execute(
        select(TelegramReferral).where(
            TelegramReferral.referred_user_id == referred_user_id
        )
    )
    existing = existing_result.scalar_one_or_none()
    if existing:
        return existing

    code_result = await db.execute(
        select(ReferralCode).where(
            ReferralCode.code == referral_code.strip().upper(),
            ReferralCode.is_active.is_(True),
        )
    )
    code = code_result.scalar_one_or_none()
    if not code or code.user_id == referred_user_id:
        return None

    attribution = TelegramReferral(
        referrer_user_id=code.user_id,
        referred_user_id=referred_user_id,
        referral_code_id=code.id,
    )
    try:
        async with db.begin_nested():
            db.add(attribution)
            await db.flush()
        return attribution
    except IntegrityError:
        result = await db.execute(
            select(TelegramReferral).where(
                TelegramReferral.referred_user_id == referred_user_id
            )
        )
        return result.scalar_one_or_none()


async def get_or_create_telegram_user(
    db: AsyncSession,
    telegram_user_data: Dict[str, Any],
    referral_start_param: str | None = None,
) -> Tuple[User, ReferralCode]:
    """
    Find existing Telegram user or create a new user with a unique referral code.
    Updates basic profile information if changed.
    """
    telegram_id = telegram_user_data.get("id")
    if not telegram_id:
        raise ValueError("Telegram user data missing required 'id' field.")

    username = telegram_user_data.get("username")
    first_name = telegram_user_data.get("first_name")
    last_name = telegram_user_data.get("last_name")
    photo_url = telegram_user_data.get("photo_url")

    for _ in range(3):
        stmt = (
            select(User)
            .options(selectinload(User.referral_code))
            .where(User.telegram_id == int(telegram_id))
        )
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()

        if user:
            if not user.is_active:
                raise PermissionError("This affiliate account has been deleted or deactivated.")
            if user.username != username:
                user.username = username
            if user.first_name != first_name:
                user.first_name = first_name
            if user.last_name != last_name:
                user.last_name = last_name
            if user.photo_url != photo_url:
                user.photo_url = photo_url
            referral_code = user.referral_code or await generate_unique_referral_code_for_user(db, user.id)
            if referral_start_param:
                await establish_telegram_referral(db, user.id, referral_start_param)
            await db.commit()
            await db.refresh(user)
            await db.refresh(user, attribute_names=["referral_code"])
            referral_code = user.referral_code
            return user, referral_code
        else:
            new_user = User(telegram_id=int(telegram_id), username=username, first_name=first_name,
                            last_name=last_name, photo_url=photo_url, is_active=True)
            db.add(new_user)
            try:
                await db.flush()  # Assigns new_user.id
                referral_code = await generate_unique_referral_code_for_user(db, new_user.id)
                if referral_start_param:
                    await establish_telegram_referral(
                        db,
                        new_user.id,
                        referral_start_param,
                    )
                await db.commit()
                await db.refresh(new_user)
                return new_user, referral_code
            except IntegrityError:
                await db.rollback()
                await asyncio.sleep(0)

    raise RuntimeError("Unable to create or retrieve Telegram user after concurrent insert retries.")
