"""Add referral status constraint.

Revision ID: 8c42f14d9b71
Revises: 1adaac4a3129
Create Date: 2026-08-31 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


revision: str = "8c42f14d9b71"
down_revision: Union[str, None] = "1adaac4a3129"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("referrals") as batch_op:
        batch_op.create_check_constraint(
            "ck_referrals_status",
            "status IN ('verified', 'pending', 'rejected')",
        )


def downgrade() -> None:
    with op.batch_alter_table("referrals") as batch_op:
        batch_op.drop_constraint("ck_referrals_status", type_="check")
