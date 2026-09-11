import json
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select, func
from sqlalchemy.orm import aliased, selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.auth import get_current_admin
from app.db.models import AuditLog, User, Referral, ReferralCode, PayoutDetails, Broadcast
from app.db.session import AsyncSessionLocal
from app.services.broadcast_service import deliver_broadcast
from app.db.session import get_db

router = APIRouter(prefix="/admin", tags=["Administration"])
class BroadcastRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4096)

    @field_validator("message")
    @classmethod
    def message_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("message must not be blank")
        return value

async def _audit(db, actor, action, target=None, metadata=None):
    db.add(AuditLog(actor_user_id=actor.id, action=action, target_user_id=getattr(target, "id", None), metadata_json=json.dumps(metadata or {})))
    await db.commit()


def _user_summary(user: User) -> dict:
    return {
        "id": user.id,
        "telegram_id": user.telegram_id,
        "username": user.username,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "photo_url": user.photo_url,
    }


@router.get("/affiliates")
async def affiliates(current=Depends(get_current_admin), db: AsyncSession = Depends(get_db)):
    referral_counts = (
        select(Referral.referrer_id, func.count(Referral.id).label("referral_count"))
        .group_by(Referral.referrer_id)
        .subquery()
    )
    rows = (
        await db.execute(
            select(User, func.coalesce(referral_counts.c.referral_count, 0))
            .join(ReferralCode, ReferralCode.user_id == User.id)
            .outerjoin(referral_counts, referral_counts.c.referrer_id == User.id)
            .options(selectinload(User.referral_code))
            .where(
                User.is_active.is_(True),
                User.account_status.in_(("ACTIVE", "REVOKED")),
                ReferralCode.is_active.is_(True),
            )
            .order_by(
                User.created_at.desc(),
            )
        )
    ).all()
    return [
        {
            "id": user.id,
            "telegram_id": user.telegram_id,
            "username": user.username,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "photo_url": user.photo_url,
            "account_status": user.account_status,
            "is_admin": user.is_admin,
            "is_protected_admin": user.is_protected_admin,
            "created_at": user.created_at,
            "referral_code": user.referral_code.code if user.referral_code else None,
            "referral_count": referral_count,
        }
        for user, referral_count in rows
    ]

@router.get("/audit-logs")
async def audit_logs(current=Depends(get_current_admin), db: AsyncSession = Depends(get_db)):
    actor = aliased(User)
    target = aliased(User)
    rows = (
        await db.execute(
            select(AuditLog, actor, target)
            .join(actor, AuditLog.actor_user_id == actor.id)
            .outerjoin(target, AuditLog.target_user_id == target.id)
            .order_by(AuditLog.created_at.desc())
        )
    ).all()
    return [
        {
            "id": log.id,
            "action": log.action,
            "actor": _user_summary(actor_user),
            "target": _user_summary(target_user) if target_user else None,
            "metadata_json": log.metadata_json,
            "created_at": log.created_at,
        }
        for log, actor_user, target_user in rows
    ]

@router.get("/administrators")
async def administrators(current=Depends(get_current_admin), db: AsyncSession = Depends(get_db)):
    rows = (
        await db.execute(
            select(User)
            .where(User.is_admin.is_(True), User.is_active.is_(True))
            .order_by(User.created_at.desc())
        )
    ).scalars().all()
    return [
        {
            **_user_summary(user),
            "account_status": user.account_status,
            "is_admin": user.is_admin,
            "is_protected_admin": user.is_protected_admin,
            "created_at": user.created_at,
        }
        for user in rows
    ]

@router.get("/affiliates/{user_id}")
async def affiliate_detail(user_id: int, current=Depends(get_current_admin), db: AsyncSession = Depends(get_db)):
    user = (
        await db.execute(
            select(User)
            .options(selectinload(User.referral_code))
            .where(User.id == user_id)
        )
    ).scalar_one_or_none()
    if not user: raise HTTPException(404, "Affiliate not found")
    referral_count = await db.scalar(
        select(func.count(Referral.id)).where(Referral.referrer_id == user.id)
    )
    return {
        **_user_summary(user),
        "account_status": user.account_status,
        "is_active": user.is_active,
        "is_admin": user.is_admin,
        "is_protected_admin": user.is_protected_admin,
        "created_at": user.created_at,
        "referral_code": user.referral_code.code if user.referral_code else None,
        "referral_count": referral_count or 0,
    }

@router.get("/referrals")
async def all_referrals(affiliate_id: int | None = None, current=Depends(get_current_admin), db: AsyncSession = Depends(get_db)):
    stmt = (
        select(Referral, User)
        .join(User, Referral.referrer_id == User.id)
        .order_by(Referral.created_at.desc())
    )
    if affiliate_id is not None: stmt = stmt.where(Referral.referrer_id == affiliate_id)
    rows = (await db.execute(stmt)).all()
    return [
        {
            "id": referral.id,
            "referrer": _user_summary(referrer),
            "candidate_email": referral.candidate_email,
            "candidate_telegram_handle": referral.candidate_telegram_handle,
            "status": referral.status,
            "created_at": referral.created_at,
        }
        for referral, referrer in rows
    ]

@router.get("/referrals/{referral_id}")
async def referral_detail(referral_id: int, current=Depends(get_current_admin), db: AsyncSession = Depends(get_db)):
    row = (
        await db.execute(
            select(Referral, User)
            .join(User, Referral.referrer_id == User.id)
            .where(Referral.id == referral_id)
        )
    ).first()
    if not row: raise HTTPException(404, "Referral not found")
    referral, referrer = row
    return {
        "id": referral.id,
        "referrer": _user_summary(referrer),
        "candidate_email": referral.candidate_email,
        "candidate_telegram_handle": referral.candidate_telegram_handle,
        "status": referral.status,
        "created_at": referral.created_at,
    }

@router.get("/affiliates/{user_id}/payout")
async def payout(user_id: int, current=Depends(get_current_admin), db: AsyncSession = Depends(get_db)):
    row = (await db.execute(select(PayoutDetails).where(PayoutDetails.user_id == user_id))).scalar_one_or_none()
    if not row: raise HTTPException(404, "Payout details not found")
    return row

@router.get('/broadcasts')
async def broadcasts(current=Depends(get_current_admin), db: AsyncSession = Depends(get_db)):
    rows = (
        await db.execute(
            select(Broadcast, User)
            .join(User, Broadcast.actor_user_id == User.id)
            .order_by(Broadcast.created_at.desc())
        )
    ).all()
    return [
        {
            "id": broadcast.id,
            "actor": _user_summary(actor),
            "message": broadcast.message,
            "status": broadcast.status,
            "target_count": broadcast.target_count,
            "success_count": broadcast.success_count,
            "failed_count": broadcast.failed_count,
            "created_at": broadcast.created_at,
            "completed_at": broadcast.completed_at,
        }
        for broadcast, actor in rows
    ]

@router.post('/broadcasts', status_code=202)
async def create_broadcast(payload: BroadcastRequest, background_tasks: BackgroundTasks, current=Depends(get_current_admin), db: AsyncSession = Depends(get_db)):
    b=Broadcast(actor_user_id=current[0].id,message=payload.message,status='QUEUED'); db.add(b); await db.commit(); await db.refresh(b)
    background_tasks.add_task(deliver_broadcast,b.id,AsyncSessionLocal)
    return {
        "id": b.id,
        "actor": _user_summary(current[0]),
        "message": b.message,
        "status": b.status,
        "target_count": b.target_count,
        "success_count": b.success_count,
        "failed_count": b.failed_count,
        "created_at": b.created_at,
        "completed_at": b.completed_at,
    }

@router.post("/affiliates/{user_id}/revoke")
async def revoke(user_id: int, current=Depends(get_current_admin), db: AsyncSession = Depends(get_db)):
    target = await db.get(User, user_id)
    if not target: raise HTTPException(404, "Affiliate not found")
    if not target.is_active: raise HTTPException(400, "Deleted affiliate lifecycles cannot be revoked")
    if target.account_status == "REVOKED": raise HTTPException(400, "Affiliate is already revoked")
    target.account_status = "REVOKED"; target.is_active = True
    await _audit(db, current[0], "affiliate_revoked", target)
    return {"status": target.account_status}

@router.post("/affiliates/{user_id}/restore")
async def restore(user_id: int, current=Depends(get_current_admin), db: AsyncSession = Depends(get_db)):
    target = await db.get(User, user_id)
    if not target: raise HTTPException(404, "Affiliate not found")
    if not target.is_active: raise HTTPException(400, "Deleted affiliate lifecycles cannot be restored")
    if target.account_status != "REVOKED": raise HTTPException(400, "Only revoked affiliates can be restored")
    target.account_status = "ACTIVE"; target.is_active = True
    await _audit(db, current[0], "affiliate_restored", target)
    return {"status": target.account_status}

@router.delete("/administrators/{user_id}")
async def remove_admin(user_id: int, current=Depends(get_current_admin), db: AsyncSession = Depends(get_db)):
    target = await db.get(User, user_id)
    if not target: raise HTTPException(404, "User not found")
    if target.is_protected_admin: raise HTTPException(403, "Protected administrator cannot be removed")
    target.is_admin = False
    await _audit(db, current[0], "administrator_removed", target)
    return {"status": "ok"}

@router.post("/administrators/{user_id}/demote")
async def demote_admin(user_id: int, current=Depends(get_current_admin), db: AsyncSession = Depends(get_db)):
    target = await db.get(User, user_id)
    if not target: raise HTTPException(404, "User not found")
    if target.is_protected_admin: raise HTTPException(403, "Protected administrator cannot be demoted")
    target.is_admin = False
    await _audit(db, current[0], "administrator_removed", target)
    return {"status": "ok"}

@router.post("/administrators/{user_id}")
async def add_admin(user_id: int, current=Depends(get_current_admin), db: AsyncSession = Depends(get_db)):
    target = await db.get(User, user_id)
    if not target: raise HTTPException(404, "User not found")
    target.is_admin = True
    await _audit(db, current[0], "administrator_added", target)
    return {"status": "ok"}
