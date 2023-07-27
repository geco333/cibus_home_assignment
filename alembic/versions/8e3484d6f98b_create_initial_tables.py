"""Create initial tables

Revision ID: 8e3484d6f98b
Revises: 
Create Date: 2023-07-26 19:54:47.553717

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = '8e3484d6f98b'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'users',
        sa.Column('id', sa.Integer, primary_key=True, index=True),
        sa.Column('username', sa.String(255), unique=True, index=True),
        sa.Column('hashed_password', sa.String(255)),
        sa.Column('is_active', sa.Boolean),
    )

    op.create_table(
        'items',
        sa.Column('id', sa.Integer, primary_key=True, index=True),
        sa.Column('title', sa.String(255), index=True),
        sa.Column('description', sa.String(255), index=True),
        sa.Column('owner_id', sa.Integer),
    )


def downgrade() -> None:
    pass
