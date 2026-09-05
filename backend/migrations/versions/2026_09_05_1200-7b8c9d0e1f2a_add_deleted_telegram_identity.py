"""Preserve deleted Telegram identities for account re-registration.

Revision ID: 7b8c9d0e1f2a
Revises: 6a7b8c9d0e1f
Create Date: 2026-09-05 12:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "7b8c9d0e1f2a"
down_revision: Union[str, None] = "6a7b8c9d0e1f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("deleted_telegram_id", sa.BigInteger(), nullable=True))
    op.create_index(op.f("ix_users_deleted_telegram_id"), "users", ["deleted_telegram_id"], unique=False)
    op.execute(
        "UPDATE users SET deleted_telegram_id = telegram_id, "
        "telegram_id = -9223372036854775807 + id WHERE is_active = false"
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_users_deleted_telegram_id"), table_name="users")
    op.drop_column("users", "deleted_telegram_id")
