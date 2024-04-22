"""add AsynExample

Revision ID: 5892cac5659a
Revises: 4e00a6115607
Create Date: 2024-04-21 21:37:48.522187

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5892cac5659a'
down_revision: Union[str, None] = '4e00a6115607'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('async_example',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=255), nullable=True),
    sa.Column('description', sa.String(length=255), nullable=True),
    sa.Column('create_date', sa.DateTime(), nullable=True),
    sa.Column('modify_date', sa.DateTime(), nullable=True),
    sa.Column('user_id', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_async_example_user_id_users')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_async_example'))
    )
    op.create_index(op.f('ix_async_example_create_date'), 'async_example', ['create_date'], unique=False)
    op.create_index(op.f('ix_async_example_description'), 'async_example', ['description'], unique=False)
    op.create_index(op.f('ix_async_example_id'), 'async_example', ['id'], unique=False)
    op.create_index(op.f('ix_async_example_modify_date'), 'async_example', ['modify_date'], unique=False)
    op.create_index(op.f('ix_async_example_name'), 'async_example', ['name'], unique=False)
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f('ix_async_example_name'), table_name='async_example')
    op.drop_index(op.f('ix_async_example_modify_date'), table_name='async_example')
    op.drop_index(op.f('ix_async_example_id'), table_name='async_example')
    op.drop_index(op.f('ix_async_example_description'), table_name='async_example')
    op.drop_index(op.f('ix_async_example_create_date'), table_name='async_example')
    op.drop_table('async_example')
    # ### end Alembic commands ###