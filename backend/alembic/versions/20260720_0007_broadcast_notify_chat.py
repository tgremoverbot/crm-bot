"""add broadcasts.notify_chat_id

Broadcasts started from the bot's admin mode ("Send to everyone") report their
delivery result back to the admin who triggered them. The reporting chat is
stored on the broadcast itself so the report still goes out when sending is
picked up by the scheduler in a later request.

Revision ID: 20260720_0007
Revises: 20260703_0006
Create Date: 2026-07-20

"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260720_0007"
down_revision = "20260703_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "broadcasts",
        sa.Column("notify_chat_id", sa.BigInteger(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("broadcasts", "notify_chat_id")
