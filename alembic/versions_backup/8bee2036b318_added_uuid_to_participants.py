"""Added UUID to participants

Revision ID: 8bee2036b318
Revises: 39946b426ce0
Create Date: 2026-08-15 18:39:23.490188

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "8bee2036b318"
down_revision: Union[str, Sequence[str], None] = "39946b426ce0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # PostgreSQL UUID generation
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")

    # 1. Add UUID column temporarily nullable
    op.add_column(
        "conversation_participants",
        sa.Column(
            "id",
            sa.Uuid(),
            nullable=True,
        ),
    )

    # 2. Generate UUID for all existing rows
    op.execute(
        """
        UPDATE conversation_participants
        SET id = gen_random_uuid()
        WHERE id IS NULL
        """
    )

    # 3. Make UUID required
    op.alter_column(
        "conversation_participants",
        "id",
        nullable=False,
    )

    # 4. Remove the old composite primary key
    op.drop_constraint(
        "conversation_participants_pkey",
        "conversation_participants",
        type_="primary",
    )

    # 5. Make the new UUID the primary key
    op.create_primary_key(
        "conversation_participants_pkey",
        "conversation_participants",
        ["id"],
    )

    # 6. Keep conversation_id + user_id unique
    op.create_unique_constraint(
        "uq_conversation_participant",
        "conversation_participants",
        ["conversation_id", "user_id"],
    )


def downgrade() -> None:
    # Remove unique constraint
    op.drop_constraint(
        "uq_conversation_participant",
        "conversation_participants",
        type_="unique",
    )

    # Remove UUID primary key
    op.drop_constraint(
        "conversation_participants_pkey",
        "conversation_participants",
        type_="primary",
    )

    # Restore composite primary key
    op.create_primary_key(
        "conversation_participants_pkey",
        "conversation_participants",
        ["conversation_id", "user_id"],
    )

    # Remove UUID column
    op.drop_column(
        "conversation_participants",
        "id",
    )