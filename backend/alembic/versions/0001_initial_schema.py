"""create initial schema

Revision ID: 0001
Revises: 
Create Date: 2026-10-06

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# Revision identifiers, used by Alembic.
revision: str = '0001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Define Enum safely
user_role_enum = postgresql.ENUM('admin', 'user', name='user_role')

def upgrade() -> None:
    # Safe enum creation (won't fail if it exists in Supabase)
    user_role_enum.create(op.get_bind(), checkfirst=True)

    # Place your table creation logic here:
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('email', sa.String(), nullable=False, unique=True),
        sa.Column('role', user_role_enum, nullable=False),
    )


def downgrade() -> None:
    op.drop_table('users')
    user_role_enum.drop(op.get_bind(), checkfirst=True)