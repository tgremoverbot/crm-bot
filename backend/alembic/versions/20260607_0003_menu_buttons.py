"""add menu_buttons table

Revision ID: 20260607_0003
Revises: 20260519_0002
Create Date: 2026-06-07

"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260607_0003"
down_revision = "20260519_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "menu_buttons",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("label", sa.String(128), nullable=False),
        sa.Column("row", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("action_kind", sa.String(16), nullable=False, server_default="text"),
        sa.Column(
            "action_material_id",
            sa.Uuid(),
            sa.ForeignKey("materials.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("action_text", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )


def downgrade() -> None:
    op.drop_table("menu_buttons")
