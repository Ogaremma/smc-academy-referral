from datetime import datetime
from typing import Any, Dict, List, Optional
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
    registration_form_url: Optional[str] = None
    recent_verified_activity: List[ReferralActivityItem]

class ReferralSummary(BaseModel):
    id: int
    name: str
    course: Optional[str] = None
    status: str
    created_at: datetime

class ReferralDetail(ReferralSummary):
    fields: Dict[str, Any]
    registered_at: Optional[datetime] = None

class ReferralsResponse(BaseModel):
    total: int
    registered: int
    referrals: List[ReferralSummary]
