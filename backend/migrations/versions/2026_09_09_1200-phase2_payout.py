from alembic import op
import sqlalchemy as sa
revision = "phase2payout001"
down_revision = "phase2admin001"
branch_labels = None
depends_on = None
def upgrade():
    op.create_table("payout_details", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False), sa.Column("account_name", sa.String(255), nullable=False), sa.Column("bank_name", sa.String(255), nullable=False), sa.Column("account_number", sa.String(64), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
def downgrade(): op.drop_table("payout_details")
