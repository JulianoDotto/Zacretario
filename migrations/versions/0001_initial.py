"""initial tables

Revision ID: 0001
Revises:
"""

import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "todos",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("owner", sa.String(64), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("done", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("done_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_todos_owner", "todos", ["owner"])

    op.create_table(
        "user_preferences",
        sa.Column("owner", sa.String(64), primary_key=True),
        sa.Column("day_start", sa.Time(), nullable=False),
        sa.Column("day_end", sa.Time(), nullable=False),
        sa.Column("blocked_weekdays", sa.String(32), nullable=False),
    )

    op.create_table(
        "conversation_messages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("owner", sa.String(64), nullable=False),
        sa.Column("role", sa.String(16), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_conversation_messages_owner", "conversation_messages", ["owner"])

    op.create_table(
        "processed_messages",
        sa.Column("message_id", sa.String(255), primary_key=True),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "google_credentials",
        sa.Column("owner", sa.String(64), primary_key=True),
        sa.Column("refresh_token", sa.Text(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("google_credentials")
    op.drop_table("processed_messages")
    op.drop_index("ix_conversation_messages_owner", table_name="conversation_messages")
    op.drop_table("conversation_messages")
    op.drop_table("user_preferences")
    op.drop_index("ix_todos_owner", table_name="todos")
    op.drop_table("todos")
