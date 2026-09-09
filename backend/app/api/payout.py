from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.auth import get_current_user
from app.db.models import PayoutDetails
from app.db.session import get_db

router = APIRouter(prefix="/payout", tags=["Payout"])
class PayoutIn(BaseModel):
    account_name: str
    bank_name: str
    account_number: str

@router.get("")
async def get_payout(current=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    row = (await db.execute(select(PayoutDetails).where(PayoutDetails.user_id == current[0].id))).scalar_one_or_none()
    if not row: raise HTTPException(404, "Payout details not found")
    return row

@router.put("")
async def save_payout(payload: PayoutIn, current=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    row = (await db.execute(select(PayoutDetails).where(PayoutDetails.user_id == current[0].id))).scalar_one_or_none()
    if row is None:
        row = PayoutDetails(user_id=current[0].id, **payload.model_dump()); db.add(row)
    else:
        for key, value in payload.model_dump().items(): setattr(row, key, value)
    await db.commit(); await db.refresh(row)
    return row
