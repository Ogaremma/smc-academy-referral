"""Remove redundant unique indexes.

Revision ID: 3f4c2b1a9d8e
Revises: 8c42f14d9b71
Create Date: 2026-09-01 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


revision: str = "3f4c2b1a9d8e"
down_revision: Union[str, None] = "8c42f14d9b71"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_index(op.f("ix_users_telegram_id"), table_name="users")
    op.drop_index(op.f("ix_referral_codes_code"), table_name="referral_codes")
    op.drop_index(
        op.f("ix_referrals_google_form_response_id"),
        table_name="referrals",
    )


def downgrade() -> None:
    op.create_index(
        op.f("ix_referrals_google_form_response_id"),
        "referrals",
        ["google_form_response_id"],
        unique=True,
    )
    op.create_index(
        op.f("ix_referral_codes_code"),
        "referral_codes",
        ["code"],
        unique=True,
    )
    op.create_index(
        op.f("ix_users_telegram_id"),
        "users",
        ["telegram_id"],
        unique=True,
    )
