from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict


class ReferralActivityItem(BaseModel):
    id: int
    status: str
    verified_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class DashboardResponse(BaseModel):
    total_verified_referrals: int
    pending_referrals: int = 0
    personal_referral_link: str
    recent_verified_activity: List[ReferralActivityItem]
