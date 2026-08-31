from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.models import ReferralCode
from app.db.session import get_db
from app.services.referral_service import build_google_form_prefill_url

router = APIRouter(tags=["Referrals"])


@router.get("/r/{code}")
async def redirect_referral(
    code: str,
    db: AsyncSession = Depends(get_db),
):
    """Validate a referral code and redirect to the pre-filled Google Form."""
    cleaned_code = code.strip().upper()
    result = await db.execute(
        select(ReferralCode).where(
            ReferralCode.code == cleaned_code,
            ReferralCode.is_active.is_(True),
        )
    )

    if result.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Referral code not found or inactive",
        )

    if not settings.GOOGLE_FORM_REFERRAL_ENTRY_ID:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google Form referral field is not configured",
        )

    return RedirectResponse(
        url=build_google_form_prefill_url(cleaned_code),
        status_code=status.HTTP_307_TEMPORARY_REDIRECT,
    )
