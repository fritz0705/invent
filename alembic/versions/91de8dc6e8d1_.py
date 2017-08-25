"""empty message

Revision ID: 91de8dc6e8d1
Revises: 939b503e6789
Create Date: 2017-08-25 21:54:47.865837

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '91de8dc6e8d1'
down_revision = '939b503e6789'
branch_labels = None
depends_on = None


def upgrade():
    op.create_index("ix_items_inventory_number", "items", ["inventory_number"])


def downgrade():
    op.drop_index("ix_items_inventory_number")
