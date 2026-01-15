"""create action_items table

Revision ID: d1f2e3c4b5a6
Revises: a2b3c4d5e6f7
Create Date: 2026-01-15

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "d1f2e3c4b5a6"
down_revision = "a2b3c4d5e6f7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "action_items",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, unique=True),
        sa.Column("meeting_id", sa.Integer(), sa.ForeignKey("meetings.id"), nullable=False),
        sa.Column("description", sa.String(length=1024), nullable=False),
        sa.Column("assignee", sa.String(length=255), nullable=True),
        sa.Column("deadline", sa.DateTime(), nullable=True),
        sa.Column("priority", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False, server_default=sa.text("'To Do'")),
        sa.Column("is_overdue", sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
    )
    op.create_index("ix_action_items_meeting_id", "action_items", ["meeting_id"])


def downgrade() -> None:
    op.drop_index("ix_action_items_meeting_id", table_name="action_items")
    op.drop_table("action_items")
