from typing import Tuple
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.db.models import ReferralCode, User
from app.db.session import get_db
from app.schemas.referral import DashboardResponse
from app.schemas.user import UserProfileResponse, UserRead
from app.services.referral_service import get_user_dashboard

router = APIRouter(prefix="/user", tags=["User"])


@router.get("/me", response_model=UserProfileResponse)
async def get_current_user_profile(
    current_user_data: Tuple[User, ReferralCode] = Depends(get_current_user),
):
    """
    Return profile and personal referral code for authenticated user.
    """
    user, ref_code = current_user_data
    return UserProfileResponse(
        user=UserRead.model_validate(user),
        referral_code=ref_code.code,
    )


@router.get("/dashboard", response_model=DashboardResponse)
async def get_dashboard_data(
    current_user_data: Tuple[User, ReferralCode] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Return dashboard statistics for authenticated user.
    WE ONLY COUNT SUCCESSFUL GOOGLE FORM SUBMISSIONS.
    No rankings, leaderboards, or click counters are exposed.
    """
    user, ref_code = current_user_data
    return await get_user_dashboard(db, user.id, ref_code.code)
