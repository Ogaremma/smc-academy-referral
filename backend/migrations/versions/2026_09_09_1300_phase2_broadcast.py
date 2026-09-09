from alembic import op
import sqlalchemy as sa
revision='phase2broadcast001'; down_revision='phase2payout001'; branch_labels=None; depends_on=None
def upgrade():
 op.create_table('broadcasts',sa.Column('id',sa.Integer(),primary_key=True),sa.Column('actor_user_id',sa.Integer(),sa.ForeignKey('users.id',ondelete='RESTRICT'),nullable=False),sa.Column('message',sa.Text(),nullable=False),sa.Column('status',sa.String(24),server_default='QUEUED',nullable=False),sa.Column('target_count',sa.Integer(),server_default='0',nullable=False),sa.Column('success_count',sa.Integer(),server_default='0',nullable=False),sa.Column('failed_count',sa.Integer(),server_default='0',nullable=False),sa.Column('error_summary',sa.Text()),sa.Column('created_at',sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False),sa.Column('started_at',sa.DateTime(timezone=True)),sa.Column('completed_at',sa.DateTime(timezone=True)))
 op.create_table('broadcast_deliveries',sa.Column('id',sa.Integer(),primary_key=True),sa.Column('broadcast_id',sa.Integer(),sa.ForeignKey('broadcasts.id',ondelete='CASCADE'),nullable=False),sa.Column('user_id',sa.Integer(),sa.ForeignKey('users.id',ondelete='CASCADE'),nullable=False),sa.Column('status',sa.String(16),nullable=False),sa.Column('error_message',sa.Text()))
 op.create_index('ix_broadcasts_actor_user_id','broadcasts',['actor_user_id'])
 op.create_index('ix_broadcast_deliveries_broadcast_id','broadcast_deliveries',['broadcast_id'])
 op.create_index('ix_broadcast_deliveries_user_id','broadcast_deliveries',['user_id'])
def downgrade(): op.drop_table('broadcast_deliveries'); op.drop_table('broadcasts')
