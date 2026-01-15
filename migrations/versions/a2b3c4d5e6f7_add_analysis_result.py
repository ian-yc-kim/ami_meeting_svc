"""add analysis_result to meetings

Revision ID: a2b3c4d5e6f7
Revises: 98a245e39c12
Create Date: 2026-01-15 02:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a2b3c4d5e6f7'
down_revision: Union[str, None] = '98a245e39c12'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add analysis_result JSON column to meetings table
    op.add_column('meetings', sa.Column('analysis_result', sa.JSON(), nullable=True))


def downgrade() -> None:
    # Remove analysis_result column from meetings table
    op.drop_column('meetings', 'analysis_result')
