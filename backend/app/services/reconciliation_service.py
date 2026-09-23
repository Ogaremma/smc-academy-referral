"""Idempotent reconciliation of historical Google Form submissions.

The original Apps Script webhook stored only the attribution envelope
(``response_id``, ``referral_code``, timestamp, email, Telegram handle) and not
the submitted answers. Registrations that arrived before the fix therefore show
up as referrals without their full submission data.

This module re-imports the complete submission for those responses from the
Google Form / Sheet (through the Apps Script backfill) without ever duplicating
a referral or overwriting existing attribution:

* a referral already stored for the response id is enriched in place;
* a submission that is missing entirely is created only when the referral code
  on the submission unambiguously resolves to a known, active affiliate code;
* anything that cannot be matched safely is reported and left untouched.

Running the reconciliation repeatedly is safe: a second pass reports
``unchanged`` for everything already reconciled.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional, Sequence

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Referral, ReferralCode, WebhookLog
from app.schemas.webhook import GoogleFormWebhookPayload
from app.services.submission_service import (
    PROCESSED_STATUS,
    answers_present,
    derive_identity,
    parse_submission_fields,
    resolve_payload_referral_code,
)

CREATED = "created"
ENRICHED = "enriched"
UNCHANGED = "unchanged"
UNMATCHED = "unmatched"


@dataclass
class ReconcileOutcome:
    response_id: str
    action: str
    referral_id: Optional[int] = None
    reason: Optional[str] = None


def _normalize(value: Optional[str]) -> str:
    return (value or "").strip().lower()


def _handle_key(value: Optional[str]) -> str:
    return _normalize(value).lstrip("@")


def _submitted_at(payload: GoogleFormWebhookPayload) -> datetime:
    value = payload.submitted_at
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


async def _referral_by_response_id(
    db: AsyncSession, response_id: str
) -> Optional[Referral]:
    return (
        await db.execute(
            select(Referral).where(Referral.google_form_response_id == response_id)
        )
    ).scalar_one_or_none()


async def _referral_by_identity(
    db: AsyncSession,
    referrer_id: int,
    email: Optional[str],
    telegram: Optional[str],
) -> Optional[Referral]:
    """Find an existing referral for the same candidate under the same affiliate."""
    email_key = _normalize(email)
    telegram_key = _handle_key(telegram)
    if not email_key and not telegram_key:
        return None
    candidates = (
        await db.execute(select(Referral).where(Referral.referrer_id == referrer_id))
    ).scalars().all()
    for referral in candidates:
        if email_key and _normalize(referral.candidate_email) == email_key:
            return referral
        if telegram_key and _handle_key(referral.candidate_telegram_handle) == telegram_key:
            return referral
    return None


async def _has_stored_answers(db: AsyncSession, referral: Referral) -> bool:
    payloads = (
        await db.execute(
            select(WebhookLog.raw_payload).where(
                WebhookLog.google_form_response_id
                == referral.google_form_response_id,
                WebhookLog.status == PROCESSED_STATUS,
            )
        )
    ).scalars().all()
    return any(answers_present(raw) for raw in payloads)


def _store_submission(
    db: AsyncSession, response_id: str, raw_payload: str, now: datetime
) -> None:
    db.add(
        WebhookLog(
            google_form_response_id=response_id,
            raw_payload=raw_payload,
            status=PROCESSED_STATUS,
            error_message=None,
            processed_at=now,
        )
    )


async def reconcile_submission(
    db: AsyncSession,
    payload: GoogleFormWebhookPayload,
    *,
    dry_run: bool = False,
) -> ReconcileOutcome:
    """Reconcile a single submission without duplicating or resetting anything."""
    now = datetime.now(timezone.utc)
    raw_payload = payload.model_dump_json()
    has_answers = answers_present(raw_payload)

    existing = await _referral_by_response_id(db, payload.response_id)
    if existing is not None:
        if not has_answers:
            return ReconcileOutcome(
                payload.response_id,
                UNCHANGED,
                existing.id,
                "Submission has no answers; existing referral left untouched.",
            )
        if await _has_stored_answers(db, existing):
            return ReconcileOutcome(
                payload.response_id,
                UNCHANGED,
                existing.id,
                "Referral already has its submission answers; no change.",
            )
        if dry_run:
            return ReconcileOutcome(
                payload.response_id,
                ENRICHED,
                existing.id,
                "Would add the missing Google Form answers to the existing referral.",
            )
        _store_submission(db, existing.google_form_response_id, raw_payload, now)
        await db.commit()
        return ReconcileOutcome(
            payload.response_id,
            ENRICHED,
            existing.id,
            "Added the missing Google Form answers to the existing referral.",
        )

    code_value = resolve_payload_referral_code(raw_payload, payload.referral_code)
    if not code_value:
        return ReconcileOutcome(
            payload.response_id,
            UNMATCHED,
            None,
            "No referral code on the submission, so it cannot be attributed.",
        )
    code = (
        await db.execute(select(ReferralCode).where(ReferralCode.code == code_value))
    ).scalar_one_or_none()
    if code is None:
        return ReconcileOutcome(
            payload.response_id,
            UNMATCHED,
            None,
            f"Referral code '{code_value}' does not exist.",
        )
    if not code.is_active:
        return ReconcileOutcome(
            payload.response_id,
            UNMATCHED,
            None,
            f"Referral code '{code_value}' is inactive.",
        )
    if not has_answers:
        return ReconcileOutcome(
            payload.response_id,
            UNMATCHED,
            None,
            "No answers in the submission; refusing to create a referral without detail.",
        )

    derived_email, derived_telegram = derive_identity(parse_submission_fields(raw_payload))
    email = payload.candidate_email or derived_email
    telegram = payload.candidate_telegram_handle or derived_telegram

    twin = await _referral_by_identity(db, code.user_id, email, telegram)
    if twin is not None:
        if await _has_stored_answers(db, twin):
            return ReconcileOutcome(
                payload.response_id,
                UNCHANGED,
                twin.id,
                "An equivalent referral already exists; no duplicate created.",
            )
        if dry_run:
            return ReconcileOutcome(
                payload.response_id,
                ENRICHED,
                twin.id,
                "Would enrich the existing referral matched by candidate identity.",
            )
        _store_submission(db, twin.google_form_response_id, raw_payload, now)
        await db.commit()
        return ReconcileOutcome(
            payload.response_id,
            ENRICHED,
            twin.id,
            "Matched an existing referral by candidate identity and added its answers.",
        )

    if dry_run:
        return ReconcileOutcome(
            payload.response_id,
            CREATED,
            None,
            f"Would create a referral for affiliate code '{code_value}'.",
        )

    referral = Referral(
        referral_code_id=code.id,
        referrer_id=code.user_id,
        google_form_response_id=payload.response_id,
        candidate_email=email,
        candidate_telegram_handle=telegram,
        status="verified",
        registered_at=_submitted_at(payload),
        verified_at=now,
    )
    db.add(referral)
    _store_submission(db, payload.response_id, raw_payload, now)
    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        duplicate = await _referral_by_response_id(db, payload.response_id)
        if duplicate is not None:
            return ReconcileOutcome(
                payload.response_id,
                UNCHANGED,
                duplicate.id,
                "Referral already existed; no duplicate created.",
            )
        raise
    await db.commit()
    return ReconcileOutcome(
        payload.response_id,
        CREATED,
        referral.id,
        "Created the missing referral from the Google Form submission.",
    )


async def reconcile_submissions(
    db: AsyncSession,
    payloads: Sequence[GoogleFormWebhookPayload],
    *,
    dry_run: bool = False,
) -> list[ReconcileOutcome]:
    """Reconcile a batch of submissions, committing each safe change."""
    return [
        await reconcile_submission(db, payload, dry_run=dry_run)
        for payload in payloads
    ]
