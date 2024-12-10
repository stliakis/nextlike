"""

Revision ID: 29ccb3753028
Revises: 5eb4d80fff4f
Create Date: 2024-11-24 20:38:33.643381

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '29ccb3753028'
down_revision = '5eb4d80fff4f'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('item', sa.Column('is_dirty', sa.Boolean(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('item', 'is_dirty')
    # ### end Alembic commands ###