from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator

QUESTION_MAX_LENGTH = 512
ANSWER_MAX_LENGTH = 8192


class FormAnswer(BaseModel):
    # One Google Form answer, preserving the original question wording.
    question: str = Field(..., min_length=1, max_length=QUESTION_MAX_LENGTH)
    answer: str = Field(default="", max_length=ANSWER_MAX_LENGTH)

    @field_validator("question", mode="before")
    @classmethod
    def _truncate_question(cls, value: Any) -> Any:
        """Keep a long question label instead of rejecting the submission."""
        if isinstance(value, str) and len(value) > QUESTION_MAX_LENGTH:
            return value[:QUESTION_MAX_LENGTH]
        return value

    @field_validator("answer", mode="before")
    @classmethod
    def _truncate_answer(cls, value: Any) -> Any:
        """Keep an oversize answer instead of losing the whole registration."""
        if isinstance(value, str) and len(value) > ANSWER_MAX_LENGTH:
            return value[:ANSWER_MAX_LENGTH]
        return value


class GoogleFormWebhookPayload(BaseModel):
    response_id: str = Field(..., description="Unique Google Form response ID")
    referral_code: str = Field(
        default="",
        description=(
            "Referral code captured from the form entry. It may be a bare code, "
            "a referral link, or blank when the submission carries the code in "
            "one of its answers."
        ),
    )
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


class DiagnosticsRequest(BaseModel):
    """Optional inputs for the Apps Script configuration check."""

    referral_code: Optional[str] = Field(
        default=None,
        description="Referral code (or referral link) to resolve while checking.",
    )


class ReferralCodeDiagnostics(BaseModel):
    provided: str
    resolved: str
    exists: bool
    is_active: Optional[bool] = None
    affiliate: Optional[Dict[str, Any]] = None
    reason: Optional[str] = None


class DiagnosticsResponse(BaseModel):
    """Result of the one-call Apps Script wiring check."""

    ok: bool
    environment: str
    backend_public_url: str
    webhook_url: str
    webhook_secret_configured: bool
    referral_entry_id: Optional[str] = None
    google_form_url: str
    prefill_url: Optional[str] = None
    counts: Dict[str, int] = Field(default_factory=dict)
    webhook_log_statuses: Dict[str, int] = Field(default_factory=dict)
    referral_code: Optional[ReferralCodeDiagnostics] = None
    checked_at: datetime
