"""add source_chat_id/source_message_id to materials for exact-copy sending

Revision ID: 20260703_0005
Revises: 20260702_0004
Create Date: 2026-07-03

"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260703_0005"
down_revision = "20260702_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "materials", sa.Column("source_chat_id", sa.BigInteger(), nullable=True)
    )
    op.add_column(
        "materials", sa.Column("source_message_id", sa.BigInteger(), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("materials", "source_message_id")
    op.drop_column("materials", "source_chat_id")
