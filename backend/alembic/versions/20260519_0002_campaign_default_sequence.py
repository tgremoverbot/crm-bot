"""add default_sequence_id to campaigns

Revision ID: 20260519_0002
Revises: 20260518_0001
Create Date: 2026-05-19

"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260519_0002"
down_revision = "20260518_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "campaigns",
        sa.Column(
            "default_sequence_id",
            sa.Uuid(),
            sa.ForeignKey("sequences.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("campaigns", "default_sequence_id")
