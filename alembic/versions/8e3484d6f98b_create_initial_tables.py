"""Create initial tables

Revision ID: 8e3484d6f98b
Revises: 
Create Date: 2023-07-26 19:54:47.553717

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy import ForeignKey

# revision identifiers, used by Alembic.
revision = '8e3484d6f98b'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'users',
        sa.Column('id', sa.Integer, primary_key=True, index=True),
        sa.Column('username', sa.String, unique=True, index=True),
        sa.Column('hashed_password', sa.String),
        sa.Column('logged_in', sa.Boolean),
    )

    op.create_table(
        'messages',
        sa.Column('id', sa.Integer, primary_key=True, index=True),
        sa.Column('author_id', sa.Integer, ForeignKey("users.id")),
        sa.Column('message', sa.String, index=True),
        sa.Column('vote_count', sa.Integer, default=0),
    )


def downgrade() -> None:
    pass
