from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector

revision: str = '78445b9799f6'
down_revision: Union[str, Sequence[str], None] = '1bc5d6be88da'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)

    columns = [c['name'] for c in inspector.get_columns('calendar_sources')]

    if 'subject_mapping' not in columns:
        op.add_column('calendar_sources', sa.Column('subject_mapping', sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column('calendar_sources', 'subject_mapping')
