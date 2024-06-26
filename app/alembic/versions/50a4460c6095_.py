"""

Revision ID: 50a4460c6095
Revises: 6d360ddcaa20
Create Date: 2024-04-16 18:05:05.677399

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '50a4460c6095'
down_revision = '6d360ddcaa20'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('search_history',
    sa.Column('id', sa.BigInteger(), nullable=False),
    sa.Column('external_person_id', sa.String(), nullable=True),
    sa.Column('external_item_ids', postgresql.ARRAY(sa.String()), nullable=True),
    sa.Column('recommendation_config', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('created', sa.DateTime(), nullable=True),
    sa.Column('collection_id', sa.BigInteger(), nullable=True),
    sa.ForeignKeyConstraint(['collection_id'], ['collection.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_search_history_external_item_ids'), 'search_history', ['external_item_ids'], unique=False)
    op.create_index(op.f('ix_search_history_external_person_id'), 'search_history', ['external_person_id'], unique=False)
    op.drop_index('ix_recommendation_history_external_item_ids', table_name='recommendation_history')
    op.drop_index('ix_recommendation_history_external_person_id', table_name='recommendation_history')
    op.drop_constraint('event_related_recommendation_id_fkey', 'event', type_='foreignkey')
    op.drop_table('recommendation_history')
    op.create_foreign_key(None, 'event', 'search_history', ['related_recommendation_id'], ['id'], ondelete='CASCADE')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(None, 'event', type_='foreignkey')
    op.create_foreign_key('event_related_recommendation_id_fkey', 'event', 'recommendation_history', ['related_recommendation_id'], ['id'], ondelete='CASCADE')
    op.create_table('recommendation_history',
    sa.Column('id', sa.BIGINT(), autoincrement=True, nullable=False),
    sa.Column('external_person_id', sa.VARCHAR(), autoincrement=False, nullable=True),
    sa.Column('external_item_ids', postgresql.ARRAY(sa.VARCHAR()), autoincrement=False, nullable=True),
    sa.Column('recommendation_config', postgresql.JSONB(astext_type=sa.Text()), autoincrement=False, nullable=False),
    sa.Column('created', postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
    sa.Column('collection_id', sa.BIGINT(), autoincrement=False, nullable=True),
    sa.ForeignKeyConstraint(['collection_id'], ['collection.id'], name='recommendation_history_collection_id_fkey', ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name='recommendation_history_pkey')
    )
    op.create_index('ix_recommendation_history_external_person_id', 'recommendation_history', ['external_person_id'], unique=False)
    op.create_index('ix_recommendation_history_external_item_ids', 'recommendation_history', ['external_item_ids'], unique=False)
    op.drop_index(op.f('ix_search_history_external_person_id'), table_name='search_history')
    op.drop_index(op.f('ix_search_history_external_item_ids'), table_name='search_history')
    op.drop_table('search_history')
    # ### end Alembic commands ###
