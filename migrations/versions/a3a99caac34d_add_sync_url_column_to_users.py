"""Add sync_url column to users

Revision ID: a3a99caac34d
Revises: 7b1f8f2d6bab
Create Date: 2025-07-26 08:44:50.170180

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a3a99caac34d'
down_revision = '7b1f8f2d6bab'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('users', sa.Column('sync_url', sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column('users', 'sync_url')
