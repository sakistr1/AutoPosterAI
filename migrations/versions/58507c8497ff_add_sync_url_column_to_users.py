from alembic import op
import sqlalchemy as sa

revision = '58507c8497ff'
down_revision = 'e44e2c4dd242'
branch_labels = None
depends_on = None

def upgrade():
    op.add_column('users', sa.Column('sync_url', sa.String(), nullable=True))

def downgrade():
    with op.batch_alter_table('users') as batch_op:
        batch_op.drop_column('sync_url')
