"""initial schema

Revision ID: 20260518_0001
Revises:
Create Date: 2026-05-18

"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "20260518_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


MATERIAL_KIND = ("text", "photo", "document", "video", "link")
PARSE_MODE = ("MarkdownV2", "HTML", "none")
SEQUENCE_TRIGGER = ("campaign_join", "manual", "tag_added")
SCHEDULED_STATUS = (
    "pending",
    "processing",
    "sent",
    "failed",
    "failed_terminal",
    "cancelled",
)
SOURCE_KIND = ("sequence", "broadcast", "manual")
BROADCAST_STATUS = (
    "draft",
    "scheduled",
    "sending",
    "sent",
    "cancelled",
    "failed",
)
BROADCAST_DELIVERY_STATUS = ("pending", "sent", "failed", "skipped")


def upgrade() -> None:
    op.create_table(
        "admin_users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("id", name="pk_admin_users"),
        sa.UniqueConstraint("email", name="uq_admin_users_email"),
    )

    op.create_table(
        "campaigns",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=64), nullable=False),
        sa.Column("description", sa.String(length=1024), nullable=True),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("id", name="pk_campaigns"),
        sa.UniqueConstraint("slug", name="uq_campaigns_slug"),
    )
    op.create_index("ix_campaigns_slug", "campaigns", ["slug"], unique=False)

    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("chat_id", sa.BigInteger(), nullable=False),
        sa.Column("username", sa.String(length=64), nullable=True),
        sa.Column("first_name", sa.String(length=128), nullable=True),
        sa.Column("last_name", sa.String(length=128), nullable=True),
        sa.Column("language_code", sa.String(length=16), nullable=True),
        sa.Column("phone", sa.String(length=32), nullable=True),
        sa.Column(
            "is_blocked",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("source_campaign_id", sa.Uuid(), nullable=True),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["source_campaign_id"],
            ["campaigns.id"],
            name="fk_users_source_campaign_id_campaigns",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_users"),
        sa.UniqueConstraint("telegram_id", name="uq_users_telegram_id"),
    )
    op.create_index("ix_users_telegram_id", "users", ["telegram_id"], unique=False)
    op.create_index(
        "ix_users_source_campaign_id", "users", ["source_campaign_id"], unique=False
    )

    op.create_table(
        "segments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.String(length=1024), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("id", name="pk_segments"),
        sa.UniqueConstraint("name", name="uq_segments_name"),
    )

    op.create_table(
        "user_segments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("segment_id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_user_segments_user_id_users",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["segment_id"],
            ["segments.id"],
            name="fk_user_segments_segment_id_segments",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_user_segments"),
        sa.UniqueConstraint(
            "user_id", "segment_id", name="uq_user_segments_user_segment"
        ),
    )
    op.create_index("ix_user_segments_user_id", "user_segments", ["user_id"])
    op.create_index("ix_user_segments_segment_id", "user_segments", ["segment_id"])

    op.create_table(
        "materials",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column(
            "kind",
            sa.Enum(*MATERIAL_KIND, name="material_kind", native_enum=False, length=32),
            nullable=False,
        ),
        sa.Column("body", sa.Text(), nullable=True),
        sa.Column("file_id", sa.String(length=512), nullable=True),
        sa.Column("file_url", sa.String(length=2048), nullable=True),
        sa.Column("link_url", sa.String(length=2048), nullable=True),
        sa.Column(
            "parse_mode",
            sa.Enum(*PARSE_MODE, name="parse_mode", native_enum=False, length=16),
            nullable=False,
            server_default="MarkdownV2",
        ),
        sa.Column(
            "disable_web_page_preview",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("id", name="pk_materials"),
    )

    op.create_table(
        "sequences",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.String(length=1024), nullable=True),
        sa.Column(
            "trigger_kind",
            sa.Enum(
                *SEQUENCE_TRIGGER,
                name="sequence_trigger_kind",
                native_enum=False,
                length=32,
            ),
            nullable=False,
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("id", name="pk_sequences"),
    )

    op.create_table(
        "sequence_steps",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("sequence_id", sa.Uuid(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column(
            "delay_minutes",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column("material_id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["sequence_id"],
            ["sequences.id"],
            name="fk_sequence_steps_sequence_id_sequences",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["material_id"],
            ["materials.id"],
            name="fk_sequence_steps_material_id_materials",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_sequence_steps"),
        sa.UniqueConstraint(
            "sequence_id", "position", name="uq_sequence_steps_sequence_position"
        ),
    )
    op.create_index(
        "ix_sequence_steps_sequence_id", "sequence_steps", ["sequence_id"]
    )
    op.create_index(
        "ix_sequence_steps_material_id", "sequence_steps", ["material_id"]
    )

    op.create_table(
        "scheduled_messages",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("material_id", sa.Uuid(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                *SCHEDULED_STATUS,
                name="scheduled_message_status",
                native_enum=False,
                length=32,
            ),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "attempts", sa.Integer(), nullable=False, server_default=sa.text("0")
        ),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column(
            "source_kind",
            sa.Enum(*SOURCE_KIND, name="source_kind", native_enum=False, length=16),
            nullable=True,
        ),
        sa.Column("source_id", sa.Uuid(), nullable=True),
        sa.Column("idempotency_key", sa.String(length=255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_scheduled_messages_user_id_users",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["material_id"],
            ["materials.id"],
            name="fk_scheduled_messages_material_id_materials",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_scheduled_messages"),
        sa.UniqueConstraint(
            "idempotency_key", name="uq_scheduled_messages_idempotency_key"
        ),
    )
    op.create_index(
        "ix_scheduled_messages_user_id", "scheduled_messages", ["user_id"]
    )
    op.create_index(
        "ix_scheduled_messages_status_scheduled_at",
        "scheduled_messages",
        ["status", "scheduled_at"],
    )

    op.create_table(
        "broadcasts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("material_id", sa.Uuid(), nullable=False),
        sa.Column("segment_id", sa.Uuid(), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                *BROADCAST_STATUS,
                name="broadcast_status",
                native_enum=False,
                length=16,
            ),
            nullable=False,
            server_default="draft",
        ),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "recipient_count",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "success_count",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "failure_count",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["material_id"],
            ["materials.id"],
            name="fk_broadcasts_material_id_materials",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["segment_id"],
            ["segments.id"],
            name="fk_broadcasts_segment_id_segments",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["admin_users.id"],
            name="fk_broadcasts_created_by_admin_users",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_broadcasts"),
    )

    op.create_table(
        "broadcast_deliveries",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("broadcast_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                *BROADCAST_DELIVERY_STATUS,
                name="broadcast_delivery_status",
                native_enum=False,
                length=16,
            ),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("telegram_message_id", sa.BigInteger(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["broadcast_id"],
            ["broadcasts.id"],
            name="fk_broadcast_deliveries_broadcast_id_broadcasts",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_broadcast_deliveries_user_id_users",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_broadcast_deliveries"),
        sa.UniqueConstraint(
            "broadcast_id",
            "user_id",
            name="uq_broadcast_deliveries_broadcast_user",
        ),
    )
    op.create_index(
        "ix_broadcast_deliveries_broadcast_id",
        "broadcast_deliveries",
        ["broadcast_id"],
    )
    op.create_index(
        "ix_broadcast_deliveries_user_id", "broadcast_deliveries", ["user_id"]
    )

    op.create_table(
        "event_logs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column("type", sa.String(length=128), nullable=False),
        sa.Column(
            "payload",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'{}'"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_event_logs_user_id_users",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_event_logs"),
    )
    op.create_index(
        "ix_event_logs_user_created_at", "event_logs", ["user_id", "created_at"]
    )
    op.create_index(
        "ix_event_logs_type_created_at", "event_logs", ["type", "created_at"]
    )


def downgrade() -> None:
    op.drop_index("ix_event_logs_type_created_at", table_name="event_logs")
    op.drop_index("ix_event_logs_user_created_at", table_name="event_logs")
    op.drop_table("event_logs")

    op.drop_index(
        "ix_broadcast_deliveries_user_id", table_name="broadcast_deliveries"
    )
    op.drop_index(
        "ix_broadcast_deliveries_broadcast_id", table_name="broadcast_deliveries"
    )
    op.drop_table("broadcast_deliveries")
    op.drop_table("broadcasts")

    op.drop_index(
        "ix_scheduled_messages_status_scheduled_at", table_name="scheduled_messages"
    )
    op.drop_index("ix_scheduled_messages_user_id", table_name="scheduled_messages")
    op.drop_table("scheduled_messages")

    op.drop_index("ix_sequence_steps_material_id", table_name="sequence_steps")
    op.drop_index("ix_sequence_steps_sequence_id", table_name="sequence_steps")
    op.drop_table("sequence_steps")
    op.drop_table("sequences")

    op.drop_table("materials")

    op.drop_index("ix_user_segments_segment_id", table_name="user_segments")
    op.drop_index("ix_user_segments_user_id", table_name="user_segments")
    op.drop_table("user_segments")
    op.drop_table("segments")

    op.drop_index("ix_users_source_campaign_id", table_name="users")
    op.drop_index("ix_users_telegram_id", table_name="users")
    op.drop_table("users")

    op.drop_index("ix_campaigns_slug", table_name="campaigns")
    op.drop_table("campaigns")

    op.drop_table("admin_users")
