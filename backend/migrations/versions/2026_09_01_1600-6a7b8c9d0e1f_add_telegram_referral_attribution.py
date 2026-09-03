"""Add Telegram-native referral attribution.

Revision ID: 6a7b8c9d0e1f
Revises: 3f4c2b1a9d8e
Create Date: 2026-09-01 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "6a7b8c9d0e1f"
down_revision: Union[str, None] = "3f4c2b1a9d8e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("referral_codes") as batch_op:
        batch_op.create_unique_constraint(
            "uq_referral_codes_id_user_id",
            ["id", "user_id"],
        )
    op.create_table(
        "telegram_referrals",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("referrer_user_id", sa.Integer(), nullable=False),
        sa.Column("referred_user_id", sa.Integer(), nullable=False),
        sa.Column("referral_code_id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "referrer_user_id <> referred_user_id",
            name="ck_telegram_referrals_no_self_referral",
        ),
        sa.ForeignKeyConstraint(
            ["referral_code_id", "referrer_user_id"],
            ["referral_codes.id", "referral_codes.user_id"],
            name="fk_telegram_referrals_code_owner",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["referred_user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["referrer_user_id"],
            ["users.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "referred_user_id",
            name="uq_telegram_referrals_referred_user_id",
        ),
    )
    op.create_index(
        op.f("ix_telegram_referrals_referrer_user_id"),
        "telegram_referrals",
        ["referrer_user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_telegram_referrals_referrer_user_id"),
        table_name="telegram_referrals",
    )
    op.drop_table("telegram_referrals")
    with op.batch_alter_table("referral_codes") as batch_op:
        batch_op.drop_constraint(
            "uq_referral_codes_id_user_id",
            type_="unique",
        )
