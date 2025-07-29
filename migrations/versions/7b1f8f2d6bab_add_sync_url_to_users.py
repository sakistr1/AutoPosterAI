"""Add sync_url to users

Revision ID: 7b1f8f2d6bab
Revises: e260de4fc7ad
Create Date: 2025-07-25 18:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '7b1f8f2d6bab'
down_revision = 'e260de4fc7ad'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('users', sa.Column('sync_url', sa.String(), nullable=True))


def downgrade():
    op.drop_column('users', 'sync_url')
