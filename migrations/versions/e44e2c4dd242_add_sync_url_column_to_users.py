"""Add sync_url column to users

Revision ID: e44e2c4dd242
Revises: a3a99caac34d
Create Date: 2025-07-26 08:45:27.992833

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e44e2c4dd242'
down_revision: Union[str, Sequence[str], None] = 'a3a99caac34d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
