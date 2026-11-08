"""Add verified Seoul rental data, coverage and collection logs."""
from alembic import op
import sqlalchemy as sa

revision = '7bd102a4f901'
down_revision = '5dcd07ee7e8d'
branch_labels = None
depends_on = None

def upgrade():
    existing = set(sa.inspect(op.get_bind()).get_table_names())
    if 'collection_logs' not in existing:
        op.create_table('collection_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('region_code', sa.String(length=5), nullable=False),
        sa.Column('deal_month', sa.String(length=6), nullable=False),
        sa.Column('status', sa.String(length=16), nullable=False),
        sa.Column('source_count', sa.Integer(), nullable=True),
        sa.Column('transaction_count', sa.Integer(), nullable=True),
        sa.Column('error_code', sa.String(length=60), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=False),
        sa.Column('finished_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
        )
        with op.batch_alter_table('collection_logs', schema=None) as batch_op:
            batch_op.create_index('ix_collection_scope', ['region_code', 'deal_month', 'id'], unique=False)

    if 'regions' not in existing:
        op.create_table('regions',
        sa.Column('code', sa.String(length=5), nullable=False),
        sa.Column('name', sa.String(length=40), nullable=False),
        sa.PrimaryKeyConstraint('code'),
        sa.UniqueConstraint('name')
        )

    if 'dashboard_stats' not in existing:
        op.create_table('dashboard_stats',
        sa.Column('region_code', sa.String(length=5), nullable=False),
        sa.Column('deal_month', sa.String(length=6), nullable=False),
        sa.Column('transaction_count', sa.Integer(), nullable=False),
        sa.Column('source_count', sa.Integer(), nullable=False),
        sa.Column('calculated_at', sa.DateTime(), nullable=False),
        sa.CheckConstraint('transaction_count >= 0 AND source_count >= 0', name='ck_stats_counts'),
        sa.ForeignKeyConstraint(['region_code'], ['regions.code'], ),
        sa.PrimaryKeyConstraint('region_code', 'deal_month')
        )

    if 'real_transactions' not in existing:
        op.create_table('real_transactions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('region_code', sa.String(length=5), nullable=False),
        sa.Column('deal_month', sa.String(length=6), nullable=False),
        sa.Column('fingerprint', sa.String(length=64), nullable=False),
        sa.Column('transaction_type', sa.String(length=10), nullable=False),
        sa.Column('deposit', sa.BigInteger(), nullable=False),
        sa.Column('monthly_rent', sa.BigInteger(), nullable=False),
        sa.Column('contract_date', sa.Date(), nullable=False),
        sa.Column('area', sa.Numeric(precision=12, scale=4), nullable=False),
        sa.Column('apartment', sa.String(length=200), nullable=False),
        sa.Column('dong', sa.String(length=100), nullable=False),
        sa.Column('floor', sa.String(length=20), nullable=False),
        sa.Column('cancelled', sa.Boolean(), nullable=False),
        sa.Column('collected_at', sa.DateTime(), nullable=False),
        sa.CheckConstraint('deposit > 0 AND monthly_rent = 0 AND area > 0', name='ck_jeonse_values'),
        sa.ForeignKeyConstraint(['region_code'], ['regions.code'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('region_code', 'deal_month', 'fingerprint', name='uq_rental_scope_fingerprint')
        )
        with op.batch_alter_table('real_transactions', schema=None) as batch_op:
            batch_op.create_index('ix_rental_region_month', ['region_code', 'deal_month'], unique=False)

    table = sa.table('regions', sa.column('code'), sa.column('name'))
    if 'regions' not in existing:
        op.bulk_insert(table, [{'code': '11110', 'name': '종로구'}, {'code': '11140', 'name': '중구'}, {'code': '11170', 'name': '용산구'}, {'code': '11200', 'name': '성동구'}, {'code': '11215', 'name': '광진구'}, {'code': '11230', 'name': '동대문구'}, {'code': '11260', 'name': '중랑구'}, {'code': '11290', 'name': '성북구'}, {'code': '11305', 'name': '강북구'}, {'code': '11320', 'name': '도봉구'}, {'code': '11350', 'name': '노원구'}, {'code': '11380', 'name': '은평구'}, {'code': '11410', 'name': '서대문구'}, {'code': '11440', 'name': '마포구'}, {'code': '11470', 'name': '양천구'}, {'code': '11500', 'name': '강서구'}, {'code': '11530', 'name': '구로구'}, {'code': '11545', 'name': '금천구'}, {'code': '11560', 'name': '영등포구'}, {'code': '11590', 'name': '동작구'}, {'code': '11620', 'name': '관악구'}, {'code': '11650', 'name': '서초구'}, {'code': '11680', 'name': '강남구'}, {'code': '11710', 'name': '송파구'}, {'code': '11740', 'name': '강동구'}])

def downgrade():
    for name in ('real_transactions', 'dashboard_stats', 'collection_logs', 'regions'):
        op.drop_table(name)
