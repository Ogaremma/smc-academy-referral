from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.db.models import PayoutDetails
from app.db.session import get_db

router = APIRouter(prefix="/payout", tags=["Payout"])


class PayoutWrite(BaseModel):
    account_name: str = Field(..., min_length=2, max_length=255)
    bank_name: str = Field(..., min_length=2, max_length=255)
    account_number: str = Field(..., min_length=4, max_length=64)

    @field_validator("account_name", "bank_name", "account_number")
    @classmethod
    def not_blank(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("must not be blank")
        return cleaned


class PayoutRead(BaseModel):
    # Internal identifiers stay server-side; the Mini App never needs them.
    account_name: str
    bank_name: str
    account_number: str
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


@router.get("", response_model=PayoutRead)
async def get_payout(
    current=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    row = (
        await db.execute(
            select(PayoutDetails).where(PayoutDetails.user_id == current[0].id)
        )
    ).scalar_one_or_none()
    if not row:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Payout details not found")
    return row


@router.put("", response_model=PayoutRead)
async def save_payout(
    payload: PayoutWrite,
    current=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    row = (
        await db.execute(
            select(PayoutDetails).where(PayoutDetails.user_id == current[0].id)
        )
    ).scalar_one_or_none()
    if row is None:
        row = PayoutDetails(user_id=current[0].id, **payload.model_dump())
        db.add(row)
    else:
        for key, value in payload.model_dump().items():
            setattr(row, key, value)
    await db.commit()
    await db.refresh(row)
    return row
