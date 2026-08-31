from typing import Optional
from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.security import verify_webhook_secret
from app.db.session import get_db
from app.schemas.webhook import GoogleFormWebhookPayload, WebhookResponse
from app.services.referral_service import process_google_form_webhook

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
