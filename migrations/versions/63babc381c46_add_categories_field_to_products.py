"""Add categories field to products

Revision ID: 63babc381c46
Revises: 58507c8497ff
Create Date: 2025-07-26 18:02:33.287569

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '63babc381c46'
down_revision: Union[str, Sequence[str], None] = '58507c8497ff'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
