from typing import Tuple

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.db.models import Referral, ReferralCode, User
from app.db.session import get_db
from app.schemas.referral import (
    ReferralDetail,
    ReferralSummary,
    ReferralsResponse,
    SubmissionFieldRead,
)
from app.services.submission_service import (
    SubmissionField,
    derive_identity,
    find_value,
    load_submission_fields,
    load_submission_fields_map,
)

router = APIRouter(prefix="/referrals", tags=["Referrals"])

# Google Form question labels are free-form, so the summary falls back to the
# identity stored on the referral row when a matching question was not asked.
_NAME_LABELS = {
    "name",
    "names",
    "full name",
    "fullname",
    "candidate name",
    "student name",
    "your name",
}
_COURSE_LABELS = {
    "course",
    "program",
    "programme",
    "course program",
    "course title",
    "course of study",
    "program of study",
    "program applied for",
    "track",
}


def _display_name(fields: list[SubmissionField], referral: Referral) -> str:
    return (
        find_value(fields, _NAME_LABELS)
        or referral.candidate_telegram_handle
        or referral.candidate_email
        or "Referral"
    )


def _summary(referral: Referral, fields: list[SubmissionField]) -> ReferralSummary:
    derived_email, derived_telegram = derive_identity(fields)
    return ReferralSummary(
        id=referral.id,
        name=_display_name(fields, referral),
        email=referral.candidate_email or derived_email,
        telegram=referral.candidate_telegram_handle or derived_telegram,
        course=find_value(fields, _COURSE_LABELS, substring=True),
        status=referral.status,
        created_at=referral.created_at,
        registered_at=referral.registered_at,
        verified_at=referral.verified_at,
    )


def _field_reads(fields: list[SubmissionField]) -> list[SubmissionFieldRead]:
    return [
        SubmissionFieldRead(
            label=field.label,
            value=field.value,
            category=field.category,
            is_link=field.is_link,
        )
        for field in fields
    ]


@router.get("", response_model=ReferralsResponse)
async def list_referrals(
    current: Tuple[User, ReferralCode] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    user, _ = current
    referrals = (
        await db.execute(
            select(Referral)
            .where(Referral.referrer_id == user.id)
            .order_by(Referral.created_at.desc())
        )
    ).scalars().all()
    submission_map = await load_submission_fields_map(db, referrals)
    return ReferralsResponse(
        total=len(referrals),
        registered=sum(referral.status == "verified" for referral in referrals),
        referrals=[
            _summary(referral, submission_map.get(referral.id, []))
            for referral in referrals
        ],
    )


@router.get("/{referral_id}", response_model=ReferralDetail)
async def get_referral(
    referral_id: int,
    current: Tuple[User, ReferralCode] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    user, _ = current
    referral = (
        await db.execute(
            select(Referral).where(
                Referral.id == referral_id,
                Referral.referrer_id == user.id,
            )
        )
    ).scalar_one_or_none()
    if not referral:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Referral not found",
        )

    # The owning affiliate sees the complete submitted Google Form information,
    # including payment details and payment proof. Referrals belonging to other
    # affiliates are never reachable because the query is scoped to this user.
    fields = await load_submission_fields(db, referral)
    summary = _summary(referral, fields)
    return ReferralDetail(
        **summary.model_dump(),
        form_fields=_field_reads(fields),
    )
