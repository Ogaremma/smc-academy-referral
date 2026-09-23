"""Turn a retained Google Form submission into display-ready referral fields.

The Google Apps Script webhook persists the complete payload (including every
submitted answer) in ``webhook_logs.raw_payload``. Referral rows only store the
attribution columns, so this module is the single place that converts a stored
payload into the fields rendered by the affiliate and admin dashboards.

Affiliates and administrators see the same complete answer set for a referral:
the full Google Form submission. Only internal transport metadata (webhook
secrets, tokens, database identifiers) is stripped before display.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Iterable, Optional, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Referral, WebhookLog
from app.core.security import (
    REFERRAL_CODE_PATTERN,
    extract_referral_code,
    is_referral_code,
)

REGISTRATION = "registration"
PAYMENT = "payment"
OTHER = "other"
PROCESSED_STATUS = "processed"

# Envelope/transport keys that are never part of the submitted registration data.
INTERNAL_KEYS = {
    "response_id",
    "referral_code",
    "submitted_at",
    "candidate_email",
    "candidate_telegram_handle",
    "webhook_secret",
    "init_data",
    "access_token",
    "jwt",
    "token",
    "authorization",
    "status",
    "id",
    "user_id",
    "referrer_id",
    "referral_code_id",
    "telegram_id",
}

# Flat payload keys from the original webhook contract, mapped to a readable label.
LEGACY_LABELS = {
    "course": "Course",
    "name": "Name",
    "full_name": "Name",
    "phone": "Phone Number",
    "phone_number": "Phone Number",
}

# Answers whose question mentions any of these markers are grouped under the
# payment section. Grouping is display-only: affiliates and admins both see the
# complete answer set, including payment information and proof.
PAYMENT_KEYWORDS = (
    "payment",
    "paid",
    "pay",
    "proof",
    "screenshot",
    "screen shot",
    "receipt",
    "transaction",
    "txn",
    "transfer",
    "amount",
    "fee",
    "invoice",
    "deposit",
    "bank",
    "reference",
    "teller",
    "narration",
)

# Answers that describe the candidate or the programme they registered for.
REGISTRATION_KEYWORDS = (
    "name",
    "email",
    "mail",
    "phone",
    "mobile",
    "whatsapp",
    "telegram",
    "handle",
    "username",
    "contact",
    "course",
    "program",
    "programme",
    "track",
    "class",
    "mode",
    "online",
    "offline",
    "learning",
    "preference",
    "level",
    "gender",
    "age",
    "country",
    "city",
    "state",
    "address",
    "cohort",
    "session",
    "duration",
    "referral",
    "source",
)

EMAIL_MATCH = ("email", "mail")
TELEGRAM_MATCH = ("telegram", "handle")

MAX_VALUE_LENGTH = 4000


@dataclass(frozen=True)
class SubmissionField:
    label: str
    value: str
    category: str
    is_link: bool


def _clean_label(value: Any) -> str:
    return str(value).strip() if value is not None else ""


def _clean_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "Yes" if value else "No"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, str):
        return value.strip()
    try:
        return json.dumps(value, ensure_ascii=False)
    except (TypeError, ValueError):
        return str(value)


def _categorize(label: str) -> str:
    lowered = label.lower()
    if any(keyword in lowered for keyword in PAYMENT_KEYWORDS):
        return PAYMENT
    if any(keyword in lowered for keyword in REGISTRATION_KEYWORDS):
        return REGISTRATION
    return OTHER


def _is_link(value: str) -> bool:
    lowered = value.lower()
    return lowered.startswith("http://") or lowered.startswith("https://")


def _to_field(label: Any, value: Any) -> Optional[SubmissionField]:
    clean_label = _clean_label(label)
    clean_value = _clean_value(value)
    if not clean_label or not clean_value:
        return None
    if len(clean_value) > MAX_VALUE_LENGTH:
        clean_value = clean_value[:MAX_VALUE_LENGTH]
    return SubmissionField(
        label=clean_label,
        value=clean_value,
        category=_categorize(clean_label),
        is_link=_is_link(clean_value),
    )


def parse_submission_fields(raw_payload: Optional[str]) -> list[SubmissionField]:
    """Convert a stored webhook payload into ordered, de-duplicated fields."""
    if not raw_payload:
        return []
    try:
        payload = json.loads(raw_payload)
    except (TypeError, ValueError):
        return []
    if not isinstance(payload, dict):
        return []

    fields: list[SubmissionField] = []
    seen: set[tuple[str, str]] = set()

    def add(label: Any, value: Any) -> None:
        field = _to_field(label, value)
        if field is None:
            return
        key = (field.label.lower(), field.value.lower())
        if key in seen:
            return
        seen.add(key)
        fields.append(field)

    answers = payload.get("answers")
    if isinstance(answers, list):
        for answer in answers:
            if isinstance(answer, dict):
                add(
                    answer.get("question") or answer.get("label"),
                    answer.get("answer", answer.get("value")),
                )

    for key, value in payload.items():
        if key == "answers" or key in INTERNAL_KEYS:
            continue
        label = LEGACY_LABELS.get(key)
        if label is None:
            if not isinstance(key, str):
                continue
            label = key.replace("_", " ").replace("-", " ").strip().title()
        add(label, value)

    return fields


def answers_present(raw_payload: Optional[str]) -> bool:
    """True when a stored payload carries at least one usable form answer."""
    if not raw_payload:
        return False
    try:
        payload = json.loads(raw_payload)
    except (TypeError, ValueError):
        return False
    if not isinstance(payload, dict):
        return False
    answers = payload.get("answers")
    if not isinstance(answers, list):
        return False
    for answer in answers:
        if isinstance(answer, dict) and _clean_value(
            answer.get("answer", answer.get("value"))
        ):
            return True
    return False


def merge_identity_fields(
    fields: list[SubmissionField], referral: Referral
) -> list[SubmissionField]:
    """Append the referral row's own identity when the form did not carry it."""
    existing = {field.label.lower() for field in fields}
    merged = list(fields)
    if referral.candidate_email and "email" not in existing:
        merged.append(
            SubmissionField("Email", referral.candidate_email, REGISTRATION, False)
        )
    if referral.candidate_telegram_handle and "telegram username" not in existing:
        merged.append(
            SubmissionField(
                "Telegram Username",
                referral.candidate_telegram_handle,
                REGISTRATION,
                False,
            )
        )
    return merged


async def _processed_payloads(
    db: AsyncSession, response_ids: Sequence[str]
) -> dict[str, str]:
    """Return the most complete processed payload stored for each response id.

    Older webhook deployments stored a payload without the ``answers`` list.
    When a later reconciliation stores the complete submission for the same
    response id, the richer payload must win so the dashboards show it.
    """
    unique_ids = list(
        dict.fromkeys(response_id for response_id in response_ids if response_id)
    )
    if not unique_ids:
        return {}
    rows = (
        await db.execute(
            select(WebhookLog.google_form_response_id, WebhookLog.raw_payload)
            .where(
                WebhookLog.google_form_response_id.in_(unique_ids),
                WebhookLog.status == PROCESSED_STATUS,
            )
            .order_by(WebhookLog.id.asc())
        )
    ).all()
    payloads: dict[str, str] = {}
    for response_id, raw_payload in rows:
        if not response_id:
            continue
        current = payloads.get(response_id)
        if current is None or (
            not answers_present(current) and answers_present(raw_payload)
        ):
            payloads[response_id] = raw_payload
    return payloads


async def load_submission_fields(
    db: AsyncSession, referral: Referral
) -> list[SubmissionField]:
    payloads = await _processed_payloads(db, [referral.google_form_response_id])
    fields = parse_submission_fields(payloads.get(referral.google_form_response_id))
    return merge_identity_fields(fields, referral)


async def response_ids_with_answers(
    db: AsyncSession, response_ids: Sequence[str]
) -> set[str]:
    """Response ids whose stored payload actually carries submitted answers."""
    payloads = await _processed_payloads(db, response_ids)
    return {
        response_id
        for response_id, raw_payload in payloads.items()
        if answers_present(raw_payload)
    }


async def load_submission_fields_map(
    db: AsyncSession, referrals: Sequence[Referral]
) -> dict[int, list[SubmissionField]]:
    payloads = await _processed_payloads(
        db, [referral.google_form_response_id for referral in referrals]
    )
    return {
        referral.id: merge_identity_fields(
            parse_submission_fields(payloads.get(referral.google_form_response_id)),
            referral,
        )
        for referral in referrals
    }


def find_value(
    fields: Iterable[SubmissionField],
    labels: set[str] | tuple[str, ...],
    substring: bool = False,
) -> Optional[str]:
    """Return the first matching, non-empty answer value."""
    for field in fields:
        if field.category == PAYMENT:
            continue
        normalized = " ".join(field.label.lower().replace("/", " ").split())
        if substring:
            if any(label in normalized for label in labels):
                return field.value
        elif normalized in labels:
            return field.value
    return None


def derive_identity(
    fields: Iterable[SubmissionField],
) -> tuple[Optional[str], Optional[str]]:
    """Best-effort email/Telegram extraction from the submitted answers."""
    materialized = list(fields)
    email = find_value(materialized, EMAIL_MATCH, substring=True)
    telegram = find_value(materialized, TELEGRAM_MATCH, substring=True)
    return email, telegram


def resolve_referral_code(
    explicit: Optional[str], fields: Sequence[SubmissionField]
) -> str:
    """Attribute a submission with the strongest evidence available.

    Order of evidence: the referral code carried by the submission itself, then
    a referral code embedded in any answer (the shared referral link, the
    ``/r/<code>`` URL parameter, or a longer free-form answer). Returns an empty
    string when the submission carries no code at all, so the caller can report
    it as unattributable instead of guessing.
    """
    code = extract_referral_code(explicit)
    if is_referral_code(code):
        return code
    for field in fields:
        match = REFERRAL_CODE_PATTERN.search(field.value)
        if match:
            return match.group(0).upper()
    return code


def resolve_payload_referral_code(
    raw_payload: Optional[str], explicit: Optional[str]
) -> str:
    """Resolve the referral code from a stored payload and its envelope field."""
    return resolve_referral_code(explicit, parse_submission_fields(raw_payload))
