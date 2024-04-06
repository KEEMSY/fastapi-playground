"""create tables

Revision ID: 11837a4a899c
Revises: 6c9dcfb36874
Create Date: 2024-04-06 12:42:55.046352

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import ForeignKey

# revision identifiers, used by Alembic.
revision: str = '11837a4a899c'
down_revision: Union[str, None] = '6c9dcfb36874'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'question',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('subject', sa.String(255), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('create_date', sa.DateTime(), nullable=False),
    )

    op.create_table(
        'answer',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('create_date', sa.DateTime(), nullable=False),
        sa.Column('question_id', sa.Integer(), ForeignKey('question.id'), nullable=False),
    )

    op.create_foreign_key('fk_question', 'answer', 'question', ['question_id'], ['id'])

def downgrade() -> None:
    op.drop_table('answer')
    op.drop_table('question')