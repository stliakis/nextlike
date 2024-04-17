"""

Revision ID: 375cbf480628
Revises: 50a4460c6095
Create Date: 2024-04-16 18:10:16.564305

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '375cbf480628'
down_revision = '50a4460c6095'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('search_history', sa.Column('search_config', postgresql.JSONB(astext_type=sa.Text()), nullable=False))
    op.drop_column('search_history', 'recommendation_config')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('search_history', sa.Column('recommendation_config', postgresql.JSONB(astext_type=sa.Text()), autoincrement=False, nullable=False))
    op.drop_column('search_history', 'search_config')
    # ### end Alembic commands ###
