from alembic import op
import sqlalchemy as sa

revision = 'c010d718cfd6'
down_revision = '58507c8497ff'
branch_labels = None
depends_on = None

def upgrade():
    op.add_column('products', sa.Column('categories', sa.String(), nullable=True))

def downgrade():
    op.drop_column('products', 'categories')
