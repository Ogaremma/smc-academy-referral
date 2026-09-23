from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class FormAnswer(BaseModel):
    # One Google Form answer, preserving the original question wording.
    question: str = Field(..., min_length=1, max_length=512)
    answer: str = Field(default="", max_length=8192)


class GoogleFormWebhookPayload(BaseModel):
    response_id: str = Field(..., description="Unique Google Form response ID")
    referral_code: str = Field(..., description="Referral code captured from form entry")
    candidate_email: Optional[str] = Field(None, description="Candidate email address if collected")
    candidate_telegram_handle: Optional[str] = Field(None, description="Candidate Telegram username if collected")
    submitted_at: datetime = Field(..., description="Actual Google Form submission timestamp")
    answers: List[FormAnswer] = Field(
        default_factory=list,
        description="Every answer submitted with the Google Form response.",
    )


class WebhookResponse(BaseModel):
    success: bool
    message: str
    referral_id: Optional[int] = None


class ReconcileRequest(BaseModel):
    """Historical Google Form responses re-imported by the Apps Script backfill."""

    dry_run: bool = Field(
        default=False,
        description="Report what would happen without writing any change.",
    )
    responses: List[GoogleFormWebhookPayload] = Field(
        default_factory=list,
        max_length=1000,
        description="Complete submissions to reconcile against existing referrals.",
    )


class ReconcileResult(BaseModel):
    response_id: str
    action: str
    referral_id: Optional[int] = None
    reason: Optional[str] = None


class ReconcileResponse(BaseModel):
    total: int
    created: int
    enriched: int
    unchanged: int
    unmatched: int
    dry_run: bool
    results: List[ReconcileResult]
