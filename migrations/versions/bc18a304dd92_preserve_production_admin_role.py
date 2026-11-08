"""Match the existing production admin field without changing assigned roles."""
from alembic import op
import sqlalchemy as sa

revision = 'bc18a304dd92'
down_revision = '7bd102a4f901'
branch_labels = None
depends_on = None


def upgrade():
    columns = {column['name'] for column in sa.inspect(op.get_bind()).get_columns('user')}
    if 'is_admin' not in columns:
        op.add_column('user', sa.Column('is_admin', sa.Boolean(), nullable=False, server_default=sa.false()))


def downgrade():
    # This column predates the dashboard on production. Never delete role data.
    pass
