from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.security import extract_referral_code
from app.core.security import verify_webhook_secret
from app.db.models import Referral, ReferralCode, User, WebhookLog
from app.db.session import get_db
from app.schemas.webhook import (
    DiagnosticsRequest,
    DiagnosticsResponse,
    GoogleFormWebhookPayload,
    ReconcileRequest,
    ReconcileResponse,
    ReconcileResult,
    ReferralCodeDiagnostics,
    WebhookResponse,
)
from app.services.referral_service import (
    build_google_form_prefill_url,
    process_google_form_webhook,
)
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


@router.post("/google-form/diagnostics", response_model=DiagnosticsResponse)
async def google_form_diagnostics(
    payload: Optional[DiagnosticsRequest] = None,
    x_webhook_secret: Optional[str] = Header(None, alias="X-Webhook-Secret"),
    db: AsyncSession = Depends(get_db),
):
    """One-call check that the Google Apps Script is wired to this backend.

    The Apps Script cannot read this server's configuration, so it calls here to
    confirm the shared secret, that the database is reachable, that a referral
    code resolves to an active affiliate, and how many webhook deliveries have
    ever been recorded. Nothing is written.
    """
    if not verify_webhook_secret(x_webhook_secret, settings.WEBHOOK_SECRET):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized: Invalid or missing webhook secret key.",
        )

    provided_code = (payload.referral_code if payload else None) or ""
    resolved_code = extract_referral_code(provided_code) if provided_code else ""

    counts = {
        "users": await db.scalar(select(func.count(User.id))) or 0,
        "affiliates": await db.scalar(select(func.count(ReferralCode.id))) or 0,
        "referrals": await db.scalar(select(func.count(Referral.id))) or 0,
        "webhook_logs": await db.scalar(select(func.count(WebhookLog.id))) or 0,
    }
    status_rows = (
        await db.execute(
            select(WebhookLog.status, func.count(WebhookLog.id)).group_by(
                WebhookLog.status
            )
        )
    ).all()
    webhook_log_statuses = {log_status: count for log_status, count in status_rows}

    code_diagnostics = None
    if resolved_code:
        code_row = (
            await db.execute(
                select(ReferralCode).where(ReferralCode.code == resolved_code)
            )
        ).scalar_one_or_none()
        affiliate = None
        reason = None
        if code_row is None:
            reason = f"Referral code '{resolved_code}' does not exist."
        else:
            owner = (
                await db.execute(select(User).where(User.id == code_row.user_id))
            ).scalar_one_or_none()
            if owner is not None:
                affiliate = {
                    "id": owner.id,
                    "telegram_id": owner.telegram_id,
                    "username": owner.username,
                    "first_name": owner.first_name,
                    "last_name": owner.last_name,
                    "account_status": owner.account_status,
                    "is_active": owner.is_active,
                }
            if not code_row.is_active:
                reason = f"Referral code '{resolved_code}' is inactive."
        code_diagnostics = ReferralCodeDiagnostics(
            provided=provided_code,
            resolved=resolved_code,
            exists=code_row is not None,
            is_active=code_row.is_active if code_row is not None else None,
            affiliate=affiliate,
            reason=reason,
        )

    prefill_url = None
    if resolved_code and settings.GOOGLE_FORM_REFERRAL_ENTRY_ID:
        prefill_url = build_google_form_prefill_url(resolved_code)

    return DiagnosticsResponse(
        ok=True,
        environment=settings.ENVIRONMENT,
        backend_public_url=settings.BACKEND_PUBLIC_URL,
        webhook_url=f"{settings.BACKEND_PUBLIC_URL.rstrip('/')}/api/v1/webhooks/google-form",
        webhook_secret_configured=bool(settings.WEBHOOK_SECRET),
        referral_entry_id=settings.GOOGLE_FORM_REFERRAL_ENTRY_ID,
        google_form_url=settings.GOOGLE_FORM_BASE_URL,
        prefill_url=prefill_url,
        counts=counts,
        webhook_log_statuses=webhook_log_statuses,
        referral_code=code_diagnostics,
        checked_at=datetime.now(timezone.utc),
    )
