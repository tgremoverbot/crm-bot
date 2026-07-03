"""relax material_id FKs from RESTRICT to SET NULL and make them nullable

A message (material) should be deletable as long as it isn't used in a
*currently active* auto-flow. Historical references — an inactive sequence's
step, any broadcast, any scheduled_message — must not block deletion. To allow
that, the three foreign keys that point at materials.id switch from
ON DELETE RESTRICT to ON DELETE SET NULL, and the columns become nullable so
they can hold the NULL the database writes on delete.

Affected columns:
- scheduled_messages.material_id
- broadcasts.material_id
- sequence_steps.material_id

Revision ID: 20260703_0006
Revises: 20260703_0005
Create Date: 2026-07-03

"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260703_0006"
down_revision = "20260703_0005"
branch_labels = None
depends_on = None


# (table, fk_constraint_name) — names match the initial schema migration.
_TABLES = (
    ("scheduled_messages", "fk_scheduled_messages_material_id_materials"),
    ("broadcasts", "fk_broadcasts_material_id_materials"),
    ("sequence_steps", "fk_sequence_steps_material_id_materials"),
)


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        # SQLite (used only for isolated migration verification; production is
        # Postgres) can't ALTER a constraint in place and stores FKs without
        # names, so recreate each table via batch mode with the column made
        # nullable. The tests build their schema from the models via
        # create_all, not from this migration, so the FK ondelete behavior on
        # the migrated SQLite DB is irrelevant — only that this runs cleanly.
        for table, _fk in _TABLES:
            with op.batch_alter_table(table) as batch:
                batch.alter_column(
                    "material_id", existing_type=sa.Uuid(), nullable=True
                )
        return

    for table, fk in _TABLES:
        op.alter_column(table, "material_id", existing_type=sa.Uuid(), nullable=True)
        op.drop_constraint(fk, table, type_="foreignkey")
        op.create_foreign_key(
            fk,
            table,
            "materials",
            ["material_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        for table, _fk in _TABLES:
            with op.batch_alter_table(table) as batch:
                batch.alter_column(
                    "material_id", existing_type=sa.Uuid(), nullable=False
                )
        return

    for table, fk in _TABLES:
        op.drop_constraint(fk, table, type_="foreignkey")
        op.create_foreign_key(
            fk,
            table,
            "materials",
            ["material_id"],
            ["id"],
            ondelete="RESTRICT",
        )
        op.alter_column(table, "material_id", existing_type=sa.Uuid(), nullable=False)
