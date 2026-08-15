"""Added uuid to message receipt and delete states

Revision ID: fb5b65163ea4
Revises: 108c898cee62
Create Date: 2026-08-15 19:05:09.996362

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "fb5b65163ea4"
down_revision: Union[str, Sequence[str], None] = "108c898cee62"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # PostgreSQL UUID generator
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")

    # ============================================================
    # message_delete_state
    # ============================================================

    # 1. Add UUID column as nullable
    op.add_column(
        "message_delete_state",
        sa.Column(
            "id",
            sa.Uuid(),
            nullable=True,
        ),
    )

    # 2. Generate UUIDs for existing rows
    op.execute(
        """
        UPDATE message_delete_state
        SET id = gen_random_uuid()
        WHERE id IS NULL
        """
    )

    # 3. Make UUID NOT NULL
    op.alter_column(
        "message_delete_state",
        "id",
        nullable=False,
    )

    # 4. Remove old composite primary key
    op.drop_constraint(
        "message_delete_state_pkey",
        "message_delete_state",
        type_="primary",
    )

    # 5. Make UUID the new primary key
    op.create_primary_key(
        "message_delete_state_pkey",
        "message_delete_state",
        ["id"],
    )

    # 6. Preserve message + user uniqueness
    op.create_unique_constraint(
        "uq_message_delete_state",
        "message_delete_state",
        ["message_id", "user_id"],
    )

    # ============================================================
    # message_receipts
    # ============================================================

    # 1. Add UUID column as nullable
    op.add_column(
        "message_receipts",
        sa.Column(
            "id",
            sa.Uuid(),
            nullable=True,
        ),
    )

    # 2. Generate UUIDs for existing rows
    op.execute(
        """
        UPDATE message_receipts
        SET id = gen_random_uuid()
        WHERE id IS NULL
        """
    )

    # 3. Make UUID NOT NULL
    op.alter_column(
        "message_receipts",
        "id",
        nullable=False,
    )

    # 4. Remove old composite primary key
    op.drop_constraint(
        "message_receipts_pkey",
        "message_receipts",
        type_="primary",
    )

    # 5. Make UUID the new primary key
    op.create_primary_key(
        "message_receipts_pkey",
        "message_receipts",
        ["id"],
    )

    # 6. Preserve message + user uniqueness
    op.create_unique_constraint(
        "uq_message_receipt",
        "message_receipts",
        ["message_id", "user_id"],
    )


def downgrade() -> None:
    # ============================================================
    # message_receipts
    # ============================================================

    op.drop_constraint(
        "uq_message_receipt",
        "message_receipts",
        type_="unique",
    )

    op.drop_constraint(
        "message_receipts_pkey",
        "message_receipts",
        type_="primary",
    )

    op.create_primary_key(
        "message_receipts_pkey",
        "message_receipts",
        ["message_id", "user_id"],
    )

    op.drop_column(
        "message_receipts",
        "id",
    )

    # ============================================================
    # message_delete_state
    # ============================================================

    op.drop_constraint(
        "uq_message_delete_state",
        "message_delete_state",
        type_="unique",
    )

    op.drop_constraint(
        "message_delete_state_pkey",
        "message_delete_state",
        type_="primary",
    )

    op.create_primary_key(
        "message_delete_state_pkey",
        "message_delete_state",
        ["message_id", "user_id"],
    )

    op.drop_column(
        "message_delete_state",
        "id",
    )