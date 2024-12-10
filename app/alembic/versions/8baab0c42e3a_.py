"""

Revision ID: 8baab0c42e3a
Revises: c22bf5d01ff5
Create Date: 2024-12-08 21:40:40.876536

"""
from alembic import op
import sqlalchemy as sa
import pgvector


# revision identifiers, used by Alembic.
revision = '8baab0c42e3a'
down_revision = 'c22bf5d01ff5'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('item', sa.Column('vectors_768', pgvector.sqlalchemy.Vector(dim=768), nullable=True))
    op.create_index('item_vectors_768', 'item', ['vectors_768'], unique=False, postgresql_ops={'vectors_768': 'vector_cosine_ops'}, postgresql_using='hnsw')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index('item_vectors_768', table_name='item', postgresql_ops={'vectors_768': 'vector_cosine_ops'}, postgresql_using='hnsw')
    op.drop_column('item', 'vectors_768')
    # ### end Alembic commands ###