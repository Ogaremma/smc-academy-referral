from typing import Optional
from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.security import verify_webhook_secret
from app.db.session import get_db
from app.schemas.webhook import (
    GoogleFormWebhookPayload,
    ReconcileRequest,
    ReconcileResponse,
    ReconcileResult,
    WebhookResponse,
)
from app.services.referral_service import process_google_form_webhook
from app.services.reconciliation_service import reconcile_submissions

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


@router.post("/google-form", response_model=WebhookResponse)
async def google_form_webhook(
    payload: GoogleFormWebhookPayload,
    x_webhook_secret: Optional[str] = Header(None, alias="X-Webhook-Secret"),
    db: AsyncSession = Depends(get_db),
):
    """
    Secure webhook endpoint for Google Apps Script.
    Validates secret, enforces idempotency, logs payload, and credits verified referrals.
    """
    if not verify_webhook_secret(x_webhook_secret, settings.WEBHOOK_SECRET):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized: Invalid or missing webhook secret key.",
        )

    success, message, referral_id = await process_google_form_webhook(db, payload)

    return WebhookResponse(
        success=success,
        message=message,
        referral_id=referral_id,
    )


@router.post("/google-form/reconcile", response_model=ReconcileResponse)
async def google_form_reconcile(
    payload: ReconcileRequest,
    x_webhook_secret: Optional[str] = Header(None, alias="X-Webhook-Secret"),
    db: AsyncSession = Depends(get_db),
):
    """Backfill historical submissions without duplicating or resetting referrals.

    Used by the Apps Script backfill for registrations that arrived before the
    webhook carried the full Google Form answers. Idempotent: running it again
    only reports ``unchanged`` for responses that are already complete.
    """
    if not verify_webhook_secret(x_webhook_secret, settings.WEBHOOK_SECRET):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized: Invalid or missing webhook secret key.",
        )

    outcomes = await reconcile_submissions(
        db, payload.responses, dry_run=payload.dry_run
    )
    counts: dict[str, int] = {}
    for outcome in outcomes:
        counts[outcome.action] = counts.get(outcome.action, 0) + 1
    return ReconcileResponse(
        total=len(outcomes),
        created=counts.get("created", 0),
        enriched=counts.get("enriched", 0),
        unchanged=counts.get("unchanged", 0),
        unmatched=counts.get("unmatched", 0),
        dry_run=payload.dry_run,
        results=[
            ReconcileResult(
                response_id=outcome.response_id,
                action=outcome.action,
                referral_id=outcome.referral_id,
                reason=outcome.reason,
            )
            for outcome in outcomes
        ],
    )
