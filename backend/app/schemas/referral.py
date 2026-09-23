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
    registration_form_url: Optional[str] = None
    recent_verified_activity: List[ReferralActivityItem]


class SubmissionFieldRead(BaseModel):
    """A Google Form answer prepared for display."""

    label: str
    value: str
    category: str
    is_link: bool = False


class ReferralSummary(BaseModel):
    id: int
    name: str
    email: Optional[str] = None
    telegram: Optional[str] = None
    course: Optional[str] = None
    status: str
    created_at: datetime
    registered_at: Optional[datetime] = None
    verified_at: Optional[datetime] = None


class ReferralDetail(ReferralSummary):
    # Every answer stored for the submission. The affiliate and the admin both
    # receive the complete set; the frontend groups it into sections.
    form_fields: List[SubmissionFieldRead] = []


class ReferralsResponse(BaseModel):
    total: int
    registered: int
    referrals: List[ReferralSummary]
