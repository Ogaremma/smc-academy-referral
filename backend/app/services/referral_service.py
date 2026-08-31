from datetime import datetime, timezone
from typing import Optional, Tuple
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.models import Referral, ReferralCode, WebhookLog
from app.schemas.referral import DashboardResponse, ReferralActivityItem
from app.schemas.webhook import GoogleFormWebhookPayload


def build_personal_referral_link(code: str) -> str:
    """Construct the public backend referral URL shown on the dashboard."""
    return f"{settings.BACKEND_PUBLIC_URL.rstrip('/')}/r/{code}"


def build_google_form_prefill_url(code: str) -> str:
    """Construct the Google Form URL used only by the redirect endpoint."""
    parts = urlsplit(settings.GOOGLE_FORM_BASE_URL)
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    query["usp"] = "pp_url"
    query[settings.GOOGLE_FORM_REFERRAL_ENTRY_ID] = code
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))


async def get_user_dashboard(
    db: AsyncSession, user_id: int, user_code: str
) -> DashboardResponse:
    """
    Calculate user referral statistics for dashboard.
    WE ONLY COUNT SUCCESSFUL GOOGLE FORM SUBMISSIONS.
    No leaderboards, rankings, or click counters.
    """
    # Count verified referrals
    stmt_verified = select(func.count(Referral.id)).where(
        Referral.referrer_id == user_id, Referral.status == "verified"
    )
    res_verified = await db.execute(stmt_verified)
    total_verified = res_verified.scalar() or 0

    # Count pending referrals if applicable
    stmt_pending = select(func.count(Referral.id)).where(
        Referral.referrer_id == user_id, Referral.status == "pending"
    )
    res_pending = await db.execute(stmt_pending)
    total_pending = res_pending.scalar() or 0

    # Fetch recent verified referral activity
    stmt_activity = (
        select(Referral)
        .where(Referral.referrer_id == user_id, Referral.status == "verified")
        .order_by(Referral.verified_at.desc())
        .limit(10)
    )
    res_activity = await db.execute(stmt_activity)
    referrals_list = res_activity.scalars().all()

    activity_items = [
        ReferralActivityItem(
            id=ref.id,
            candidate_email=ref.candidate_email,
            candidate_telegram_handle=ref.candidate_telegram_handle,
            status=ref.status,
            verified_at=ref.verified_at,
        )
        for ref in referrals_list
    ]

    referral_link = build_personal_referral_link(user_code)

    return DashboardResponse(
        total_verified_referrals=total_verified,
        pending_referrals=total_pending,
        personal_referral_link=referral_link,
        recent_verified_activity=activity_items,
    )


async def process_google_form_webhook(
    db: AsyncSession, payload: GoogleFormWebhookPayload
) -> Tuple[bool, str, Optional[int]]:
    """
    Process incoming webhook from Google Apps Script.
    Enforces idempotency using google_form_response_id.
    Ensures a single form submission produces at most ONE referral credit.
    """
    now = datetime.now(timezone.utc)
    submitted_at = payload.submitted_at
    if submitted_at.tzinfo is None:
        submitted_at = submitted_at.replace(tzinfo=timezone.utc)
    else:
        submitted_at = submitted_at.astimezone(timezone.utc)
    raw_payload_str = payload.model_dump_json()

    # 1. Idempotency Check: check if form response was already processed
    stmt_existing = select(Referral).where(
        Referral.google_form_response_id == payload.response_id
    )
    res_existing = await db.execute(stmt_existing)
    existing_referral = res_existing.scalar_one_or_none()

    if existing_referral:
        # Log duplicate webhook attempt
        duplicate_log = WebhookLog(
            google_form_response_id=payload.response_id,
            raw_payload=raw_payload_str,
            status="duplicate",
            error_message="Duplicate Google Form response ID. Referral already credited.",
            processed_at=now,
        )
        db.add(duplicate_log)
        await db.commit()
        return True, "Duplicate response ID. Referral already credited.", existing_referral.id

    # 2. Validate Referral Code
    stmt_code = select(ReferralCode).where(
        ReferralCode.code == payload.referral_code.strip().upper(),
        ReferralCode.is_active.is_(True),
    )
    res_code = await db.execute(stmt_code)
    referral_code_record = res_code.scalar_one_or_none()

    if not referral_code_record:
        # Log failed attempt due to invalid referral code
        invalid_log = WebhookLog(
            google_form_response_id=payload.response_id,
            raw_payload=raw_payload_str,
            status="invalid_code",
            error_message=f"Referral code '{payload.referral_code}' not found or inactive.",
            processed_at=now,
        )
        db.add(invalid_log)
        await db.commit()
        return False, f"Invalid or inactive referral code: '{payload.referral_code}'", None

    # 3. Create verified referral record
    new_referral = Referral(
        referral_code_id=referral_code_record.id,
        referrer_id=referral_code_record.user_id,
        google_form_response_id=payload.response_id,
        candidate_email=payload.candidate_email,
        candidate_telegram_handle=payload.candidate_telegram_handle,
        status="verified",
        registered_at=submitted_at,
        verified_at=now,
    )
    db.add(new_referral)
    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        duplicate_result = await db.execute(stmt_existing)
        duplicate_referral = duplicate_result.scalar_one_or_none()
        if duplicate_referral:
            return True, "Duplicate response ID. Referral already credited.", duplicate_referral.id
        raise

    # 4. Log successful webhook processing
    success_log = WebhookLog(
        google_form_response_id=payload.response_id,
        raw_payload=raw_payload_str,
        status="processed",
        error_message=None,
        processed_at=now,
    )
    db.add(success_log)

    await db.commit()
    await db.refresh(new_referral)

    return True, "Referral successfully verified and credited.", new_referral.id
