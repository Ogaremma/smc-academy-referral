from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class GoogleFormWebhookPayload(BaseModel):
    response_id: str = Field(..., description="Unique Google Form response ID")
    referral_code: str = Field(..., description="Referral code captured from form entry")
    candidate_email: Optional[str] = Field(None, description="Candidate email address if collected")
    candidate_telegram_handle: Optional[str] = Field(None, description="Candidate Telegram username if collected")
    submitted_at: datetime = Field(..., description="Actual Google Form submission timestamp")


class WebhookResponse(BaseModel):
    success: bool
    message: str
    referral_id: Optional[int] = None
