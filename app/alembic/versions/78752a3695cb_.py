"""

Revision ID: 78752a3695cb
Revises: 1228a8e06bd1
Create Date: 2024-05-27 09:07:29.619641

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '78752a3695cb'
down_revision = '1228a8e06bd1'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('collection', sa.Column('default_embeddings_model', sa.String(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('collection', 'default_embeddings_model')
    # ### end Alembic commands ###
