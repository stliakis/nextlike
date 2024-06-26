"""

Revision ID: 9a65fb51b6e9
Revises: 56e87318c063
Create Date: 2024-05-22 11:01:52.476906

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '9a65fb51b6e9'
down_revision = '56e87318c063'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    # op.drop_index('item_vectors_1536_idx', table_name='item', postgresql_using='hnsw')
    # op.create_index('item_vectors_1536_idx', 'item', ['vectors_1536'], unique=False, postgresql_using='hnsw')
    op.create_index(op.f('ix_item_description_hash'), 'item', ['description_hash'], unique=False)
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f('ix_item_description_hash'), table_name='item')
    # ### end Alembic commands ###
