from typing import Tuple
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.core.exceptions import InvalidTokenError, TelegramAuthError
from app.core.security import (
    create_access_token,
    decode_access_token,
    validate_telegram_init_data_context,
)
from app.db.models import ReferralCode, User
from app.db.session import get_db
from app.schemas.user import TelegramAuthRequest, TokenResponse, UserRead
from app.services.user_service import get_or_create_telegram_user, generate_unique_referral_code_for_user

router = APIRouter(prefix="/auth", tags=["Authentication"])
security_bearer = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security_bearer),
    db: AsyncSession = Depends(get_db),
) -> Tuple[User, ReferralCode]:
    """FastAPI Dependency for authenticating requests via JWT Bearer token."""
    token = credentials.credentials
    try:
        payload = decode_access_token(token)
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload: missing sub",
            )
    except InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        )

    stmt = (
        select(User)
        .options(selectinload(User.referral_code))
        .where(User.id == int(user_id), User.is_active == True)
    )
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or account disabled",
        )

    return user, user.referral_code

@router.delete("/account", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(current: Tuple[User, ReferralCode] = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    user, ref_code = current
    user.deleted_telegram_id = user.telegram_id
    user.telegram_id = -9223372036854775807 + user.id
    user.is_active = False
    ref_code.is_active = False
    await db.commit()


@router.post("/telegram", response_model=TokenResponse)
async def authenticate_telegram_user(
    payload: TelegramAuthRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Authenticate a Telegram user via Mini App initData string.
    Validates HMAC-SHA256 signature, creates/fetches user, and returns a JWT token.
    """
    try:
        telegram_user_data, signed_start_param = validate_telegram_init_data_context(
            init_data_str=payload.init_data,
            bot_token=settings.BOT_TOKEN,
        )
    except TelegramAuthError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Telegram authentication failed: {str(e)}",
        )

    telegram_id = int(telegram_user_data["id"])
    if not payload.create_account:
        existing = (await db.execute(select(User).options(selectinload(User.referral_code)).where(User.telegram_id == telegram_id, User.is_active.is_(True)))).scalar_one_or_none()
        if existing:
            access_token = create_access_token(data={"sub": str(existing.id), "telegram_id": telegram_id})
            return TokenResponse(access_token=access_token, user=UserRead.model_validate(existing), referral_code=existing.referral_code.code, affiliate_active=True)
        access_token = create_access_token(data={"sub": f"telegram:{telegram_id}", "telegram_id": telegram_id, "telegram_authenticated": True})
        return TokenResponse(access_token=access_token, user=None, referral_code=None, affiliate_active=False)
    try:
        user, ref_code = await get_or_create_telegram_user(db, telegram_user_data, referral_start_param=signed_start_param)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))

    access_token = create_access_token(
        data={"sub": str(user.id), "telegram_id": user.telegram_id}
    )

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserRead.model_validate(user),
        referral_code=ref_code.code,
        affiliate_active=True,
    )

@router.post("/affiliate/register", response_model=TokenResponse)
async def register_affiliate(
    credentials: HTTPAuthorizationCredentials = Depends(security_bearer),
    db: AsyncSession = Depends(get_db),
):
    try:
        payload = decode_access_token(credentials.credentials)
        telegram_id = int(payload.get("telegram_id"))
    except (InvalidTokenError, TypeError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authentication session")
    existing = (await db.execute(select(User).options(selectinload(User.referral_code)).where(User.telegram_id == telegram_id, User.is_active.is_(True)))).scalar_one_or_none()
    if existing:
        return TokenResponse(access_token=credentials.credentials, user=UserRead.model_validate(existing), referral_code=existing.referral_code.code, affiliate_active=True)
    user = User(telegram_id=telegram_id, is_active=True)
    db.add(user)
    try:
        await db.flush()
        code = await generate_unique_referral_code_for_user(db, user.id)
        await db.commit()
        await db.refresh(user)
    except Exception:
        await db.rollback()
        existing = (await db.execute(select(User).options(selectinload(User.referral_code)).where(User.telegram_id == telegram_id, User.is_active.is_(True)))).scalar_one_or_none()
        if not existing: raise
        user, code = existing, existing.referral_code
    token = create_access_token(data={"sub": str(user.id), "telegram_id": telegram_id})
    return TokenResponse(access_token=token, user=UserRead.model_validate(user), referral_code=code.code, affiliate_active=True)
