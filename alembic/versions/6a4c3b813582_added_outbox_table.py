"""Added outbox table

Revision ID: 6a4c3b813582
Revises: 30a565b56a24
Create Date: 2026-09-05 18:08:33.152733

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "6a4c3b813582"
down_revision: Union[str, Sequence[str], None] = "30a565b56a24"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "outbox_events",
        sa.Column(
            "event_type",
            sa.VARCHAR(length=100),
            autoincrement=False,
            nullable=False,
        ),
        sa.Column(
            "channel",
            sa.VARCHAR(length=255),
            autoincrement=False,
            nullable=False,
        ),
        sa.Column(
            "payload",
            postgresql.JSONB(astext_type=sa.Text()),
            autoincrement=False,
            nullable=False,
        ),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(timezone=True),
            autoincrement=False,
            nullable=False,
        ),
        sa.Column(
            "processed_at",
            postgresql.TIMESTAMP(timezone=True),
            autoincrement=False,
            nullable=True,
        ),
        sa.Column(
            "attempts",
            sa.INTEGER(),
            autoincrement=False,
            nullable=False,
        ),
        sa.Column(
            "last_error",
            sa.TEXT(),
            autoincrement=False,
            nullable=True,
        ),
        sa.Column(
            "id",
            sa.UUID(),
            autoincrement=False,
            nullable=False,
        ),
        sa.PrimaryKeyConstraint(
            "id",
            name=op.f("outbox_events_pkey"),
        ),
    )

    op.create_index(
        op.f("ix_outbox_unprocessed"),
        "outbox_events",
        ["processed_at", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        op.f("ix_outbox_unprocessed"),
        table_name="outbox_events",
    )

    op.drop_table("outbox_events")
