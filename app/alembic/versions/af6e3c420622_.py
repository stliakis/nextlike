"""

Revision ID: af6e3c420622
Revises: 375cbf480628
Create Date: 2024-04-17 08:31:51.662920

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'af6e3c420622'
down_revision = '375cbf480628'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_index(op.f('ix_event_collection_id'), 'event', ['collection_id'], unique=False)
    op.create_index(op.f('ix_event_item_external_id'), 'event', ['item_external_id'], unique=False)
    op.create_index(op.f('ix_event_person_external_id'), 'event', ['person_external_id'], unique=False)
    op.create_index(op.f('ix_item_collection_id'), 'item', ['collection_id'], unique=False)
    op.create_index(op.f('ix_person_collection_id'), 'person', ['collection_id'], unique=False)
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f('ix_person_collection_id'), table_name='person')
    op.drop_index(op.f('ix_item_collection_id'), table_name='item')
    op.drop_index(op.f('ix_event_person_external_id'), table_name='event')
    op.drop_index(op.f('ix_event_item_external_id'), table_name='event')
    op.drop_index(op.f('ix_event_collection_id'), table_name='event')
    # ### end Alembic commands ###
