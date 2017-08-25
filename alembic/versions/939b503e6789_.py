"""empty message

Revision ID: 939b503e6789
Revises: 
Create Date: 2017-08-25 20:45:15.353211

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '939b503e6789'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('items',
        sa.Column('is_labeled', sa.Boolean, default=False))
    op.add_column('items',
        sa.Column('is_active', sa.Boolean, default=True))


def downgrade():
    op.drop_column('items', 'is_labeled')
    op.drop_column('items', 'is_active')
