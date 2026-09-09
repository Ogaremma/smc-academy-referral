import json
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.auth import get_current_admin
from app.db.models import AuditLog, User
from app.db.session import get_db

router = APIRouter(prefix="/admin", tags=["Administration"])

async def _audit(db, actor, action, target=None, metadata=None):
    db.add(AuditLog(actor_user_id=actor.id, action=action, target_user_id=getattr(target, "id", None), metadata_json=json.dumps(metadata or {})))
    await db.commit()

@router.get("/affiliates")
async def affiliates(current=Depends(get_current_admin), db: AsyncSession = Depends(get_db)):
    return (await db.execute(select(User).order_by(User.id))).scalars().all()

@router.get("/audit-logs")
async def audit_logs(current=Depends(get_current_admin), db: AsyncSession = Depends(get_db)):
    return (await db.execute(select(AuditLog).order_by(AuditLog.created_at.desc()))).scalars().all()

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
