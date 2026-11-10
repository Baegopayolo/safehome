"""Store verified map comparisons separately from legacy scores."""
from alembic import op
import sqlalchemy as sa

revision = 'fdb4f238c112'
down_revision = 'bc18a304dd92'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'map_snapshots',
        sa.Column('region_code', sa.String(5), primary_key=True),
        sa.Column('period_start', sa.Date(), nullable=False),
        sa.Column('period_end', sa.Date(), nullable=False),
        sa.Column('collected_at', sa.DateTime(), nullable=False),
        sa.Column('indicators', sa.JSON(), nullable=False),
    )


def downgrade():
    op.drop_table('map_snapshots')
