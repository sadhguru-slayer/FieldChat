"""add is_gif to messages

Revision ID: 7b8c9d0e1f2a
Revises: 6a4c3b813582
Create Date: 2026-10-02 17:21:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7b8c9d0e1f2a'
down_revision: Union[str, Sequence[str], None] = '6a4c3b813582'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('messages', sa.Column('is_gif', sa.Boolean(), server_default='false', nullable=False))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('messages', 'is_gif')
