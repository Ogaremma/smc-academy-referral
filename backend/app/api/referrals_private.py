import json
from typing import Tuple
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.auth import get_current_user
from app.db.models import Referral, ReferralCode, User, WebhookLog
from app.db.session import get_db
from app.schemas.referral import ReferralDetail, ReferralSummary, ReferralsResponse

router = APIRouter(prefix="/referrals", tags=["Referrals"])

def _summary(r: Referral) -> ReferralSummary:
    name = r.candidate_telegram_handle or r.candidate_email or "Referral"
    return ReferralSummary(id=r.id, name=name, course=None, status=r.status, created_at=r.created_at)

_LABELS = {"candidate_email": "Email", "candidate_telegram_handle": "Telegram Username", "course": "Course", "name": "Name", "full_name": "Name", "phone": "Phone Number", "phone_number": "Phone Number"}
_HIDDEN = {"response_id", "referral_code", "submitted_at", "webhook_secret", "init_data", "access_token", "jwt", "status"}

@router.get("", response_model=ReferralsResponse)
async def list_referrals(current: Tuple[User, ReferralCode] = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    user, _ = current
    rows = (await db.execute(select(Referral).where(Referral.referrer_id == user.id).order_by(Referral.created_at.desc()))).scalars().all()
    return ReferralsResponse(total=len(rows), registered=sum(r.status == "verified" for r in rows), referrals=[_summary(r) for r in rows])

@router.get("/{referral_id}", response_model=ReferralDetail)
async def get_referral(referral_id: int, current: Tuple[User, ReferralCode] = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    user, _ = current
    r = (await db.execute(select(Referral).where(Referral.id == referral_id, Referral.referrer_id == user.id))).scalar_one_or_none()
    if not r: raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Referral not found")
    log = (await db.execute(select(WebhookLog).where(WebhookLog.google_form_response_id == r.google_form_response_id, WebhookLog.status == "processed").order_by(WebhookLog.id.desc()))).scalars().first()
    fields = {}
    if log:
        try:
            raw = json.loads(log.raw_payload)
            fields = {_LABELS[k]: v for k, v in raw.items() if k in _LABELS and k not in _HIDDEN and v not in (None, "")}
        except (TypeError, ValueError): pass
    summary = _summary(r)
    return ReferralDetail(**summary.model_dump(), fields=fields, registered_at=r.registered_at)
