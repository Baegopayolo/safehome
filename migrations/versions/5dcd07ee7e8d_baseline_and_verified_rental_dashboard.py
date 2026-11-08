"""Baseline existing Flask tables without dropping or recreating user data."""
from alembic import op
import sqlalchemy as sa

revision = '5dcd07ee7e8d'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    existing = set(sa.inspect(op.get_bind()).get_table_names())
    if 'heatmap_data' not in existing:
        op.create_table('heatmap_data',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('region', sa.String(length=100), nullable=False),
        sa.Column('score', sa.Integer(), nullable=False),
        sa.Column('lat', sa.Float(), nullable=False),
        sa.Column('lng', sa.Float(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
        )
        with op.batch_alter_table('heatmap_data', schema=None) as batch_op:
            batch_op.create_index(batch_op.f('ix_heatmap_data_region'), ['region'], unique=True)

    if 'real_transaction' not in existing:
        op.create_table('real_transaction',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('lawd_cd', sa.String(length=10), nullable=False),
        sa.Column('deal_ymd', sa.String(length=6), nullable=False),
        sa.Column('region', sa.String(length=100), nullable=True),
        sa.Column('dong', sa.String(length=100), nullable=True),
        sa.Column('apt_name', sa.String(length=200), nullable=True),
        sa.Column('dong_name', sa.String(length=100), nullable=True),
        sa.Column('price', sa.Integer(), nullable=True),
        sa.Column('price_raw', sa.String(length=50), nullable=True),
        sa.Column('area', sa.String(length=50), nullable=True),
        sa.Column('floor', sa.String(length=20), nullable=True),
        sa.Column('build_year', sa.String(length=10), nullable=True),
        sa.Column('deal_date', sa.String(length=20), nullable=True),
        sa.Column('jibun', sa.String(length=50), nullable=True),
        sa.Column('region_code', sa.String(length=10), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
        )
        with op.batch_alter_table('real_transaction', schema=None) as batch_op:
            batch_op.create_index('idx_lawd_deal', ['lawd_cd', 'deal_ymd'], unique=False)
            batch_op.create_index(batch_op.f('ix_real_transaction_deal_ymd'), ['deal_ymd'], unique=False)
            batch_op.create_index(batch_op.f('ix_real_transaction_lawd_cd'), ['lawd_cd'], unique=False)
            batch_op.create_index(batch_op.f('ix_real_transaction_region'), ['region'], unique=False)

    if 'user' not in existing:
        op.create_table('user',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('username', sa.String(length=64), nullable=False),
        sa.Column('password', sa.String(length=128), nullable=False),
        sa.Column('email', sa.String(length=120), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email'),
        sa.UniqueConstraint('username')
        )

    if 'favorite' not in existing:
        op.create_table('favorite',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('region', sa.String(length=100), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
        sa.PrimaryKeyConstraint('id')
        )

    if 'notification' not in existing:
        op.create_table('notification',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('type', sa.String(length=50), nullable=False),
        sa.Column('is_read', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
        sa.PrimaryKeyConstraint('id')
        )

    if 'report' not in existing:
        op.create_table('report',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('region', sa.String(length=100), nullable=False),
        sa.Column('property_address', sa.String(length=200), nullable=True),
        sa.Column('report_type', sa.String(length=50), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
        sa.PrimaryKeyConstraint('id')
        )

    if 'review' not in existing:
        op.create_table('review',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('region', sa.String(length=100), nullable=False),
        sa.Column('rating', sa.Integer(), nullable=False),
        sa.Column('content', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
        sa.PrimaryKeyConstraint('id')
        )

    if 'search_history' not in existing:
        op.create_table('search_history',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('region', sa.String(length=100), nullable=False),
        sa.Column('search_date', sa.DateTime(), nullable=True),
        sa.Column('risk_score', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
        sa.PrimaryKeyConstraint('id')
        )


def downgrade():
    raise RuntimeError('Legacy baseline downgrade is disabled; restore a verified backup instead.')
