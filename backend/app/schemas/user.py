from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class TelegramAuthRequest(BaseModel):
    init_data: str = Field(..., description="Raw initData string received from Telegram Mini App SDK")
    start_param: Optional[str] = Field(
        None,
        description="Telegram Mini App launch parameter; signed initData remains authoritative",
    )
    create_account: bool = True


class UserRead(BaseModel):
    id: int
    telegram_id: int
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    photo_url: Optional[str] = None
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ReferralCodeRead(BaseModel):
    id: int
    code: str
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserProfileResponse(BaseModel):
    user: UserRead
    referral_code: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: Optional[UserRead] = None
    referral_code: Optional[str] = None
    affiliate_active: bool = False
