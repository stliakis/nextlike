"""

Revision ID: 1228a8e06bd1
Revises: 9a65fb51b6e9
Create Date: 2024-05-22 12:54:56.759170

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '1228a8e06bd1'
down_revision = '9a65fb51b6e9'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('item', sa.Column('scores', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('item', 'scores')
    # ### end Alembic commands ###
