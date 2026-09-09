"""Phase 2A admin roles, account status, and audit logs."""
from alembic import op
import sqlalchemy as sa

revision = "phase2admin001"
down_revision = "7b8c9d0e1f2a"
branch_labels = None
depends_on = None

def upgrade():
    op.add_column("users", sa.Column("account_status", sa.String(16), nullable=False, server_default="ACTIVE"))
    op.add_column("users", sa.Column("is_admin", sa.Boolean(), nullable=False, server_default=sa.text("0")))
    op.add_column("users", sa.Column("is_protected_admin", sa.Boolean(), nullable=False, server_default=sa.text("0")))
    op.create_table("audit_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("actor_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("action", sa.String(64), nullable=False),
        sa.Column("target_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("metadata_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_audit_logs_actor_user_id", "audit_logs", ["actor_user_id"])
    op.create_index("ix_audit_logs_target_user_id", "audit_logs", ["target_user_id"])

def downgrade():
    op.drop_table("audit_logs")
    op.drop_column("users", "is_protected_admin")
    op.drop_column("users", "is_admin")
    op.drop_column("users", "account_status")
