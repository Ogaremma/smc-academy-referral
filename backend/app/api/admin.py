import json
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.auth import get_current_admin
from app.db.models import AuditLog, User, Referral, PayoutDetails, Broadcast
from app.db.session import AsyncSessionLocal
from app.services.broadcast_service import deliver_broadcast
from app.db.session import get_db

router = APIRouter(prefix="/admin", tags=["Administration"])
class BroadcastRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4096)

async def _audit(db, actor, action, target=None, metadata=None):
    db.add(AuditLog(actor_user_id=actor.id, action=action, target_user_id=getattr(target, "id", None), metadata_json=json.dumps(metadata or {})))
    await db.commit()

@router.get("/affiliates")
async def affiliates(current=Depends(get_current_admin), db: AsyncSession = Depends(get_db)):
    return (await db.execute(select(User).order_by(User.id))).scalars().all()

@router.get("/audit-logs")
async def audit_logs(current=Depends(get_current_admin), db: AsyncSession = Depends(get_db)):
    return (await db.execute(select(AuditLog).order_by(AuditLog.created_at.desc()))).scalars().all()

@router.get("/administrators")
async def administrators(current=Depends(get_current_admin), db: AsyncSession = Depends(get_db)):
    return (await db.execute(select(User).where(User.is_admin.is_(True)))).scalars().all()

@router.get("/affiliates/{user_id}")
async def affiliate_detail(user_id: int, current=Depends(get_current_admin), db: AsyncSession = Depends(get_db)):
    user = await db.get(User, user_id)
    if not user: raise HTTPException(404, "Affiliate not found")
    return user

@router.get("/referrals")
async def all_referrals(affiliate_id: int | None = None, current=Depends(get_current_admin), db: AsyncSession = Depends(get_db)):
    stmt = select(Referral).order_by(Referral.created_at.desc())
    if affiliate_id is not None: stmt = stmt.where(Referral.referrer_id == affiliate_id)
    return (await db.execute(stmt)).scalars().all()

@router.get("/referrals/{referral_id}")
async def referral_detail(referral_id: int, current=Depends(get_current_admin), db: AsyncSession = Depends(get_db)):
    from app.api.referrals_private import get_referral
    r = await db.get(Referral, referral_id)
    if not r: raise HTTPException(404, "Referral not found")
    return {"id": r.id, "referrer_id": r.referrer_id, "candidate_email": r.candidate_email, "candidate_telegram_handle": r.candidate_telegram_handle, "status": r.status, "created_at": r.created_at}

@router.get("/affiliates/{user_id}/payout")
async def payout(user_id: int, current=Depends(get_current_admin), db: AsyncSession = Depends(get_db)):
    row = (await db.execute(select(PayoutDetails).where(PayoutDetails.user_id == user_id))).scalar_one_or_none()
    if not row: raise HTTPException(404, "Payout details not found")
    return row

@router.get('/broadcasts')
async def broadcasts(current=Depends(get_current_admin), db: AsyncSession = Depends(get_db)):
    return (await db.execute(select(Broadcast).order_by(Broadcast.created_at.desc()))).scalars().all()

@router.post('/broadcasts', status_code=202)
async def create_broadcast(payload: BroadcastRequest, background_tasks: BackgroundTasks, current=Depends(get_current_admin), db: AsyncSession = Depends(get_db)):
    b=Broadcast(actor_user_id=current[0].id,message=payload.message,status='QUEUED'); db.add(b); await db.commit(); await db.refresh(b)
    background_tasks.add_task(deliver_broadcast,b.id,AsyncSessionLocal)
    return b

@router.post("/affiliates/{user_id}/revoke")
async def revoke(user_id: int, current=Depends(get_current_admin), db: AsyncSession = Depends(get_db)):
    target = await db.get(User, user_id)
    if not target: raise HTTPException(404, "Affiliate not found")
    target.account_status = "REVOKED"; target.is_active = True
    await _audit(db, current[0], "affiliate_revoked", target)
    return {"status": target.account_status}

@router.post("/affiliates/{user_id}/restore")
async def restore(user_id: int, current=Depends(get_current_admin), db: AsyncSession = Depends(get_db)):
    target = await db.get(User, user_id)
    if not target: raise HTTPException(404, "Affiliate not found")
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
