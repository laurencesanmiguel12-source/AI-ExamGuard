"""add is_active to schools

Revision ID: 0a75dc28ca83
Revises: 72a0926edfbf
Create Date: 2026-08-21 03:35:07.565109

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0a75dc28ca83'
down_revision: Union[str, Sequence[str], None] = '72a0926edfbf'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Lets a super admin deactivate a school (blocks login for every one of its users) without
    # deleting it - server_default keeps every existing school active by default on this migration.
    op.add_column(
        'schools',
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true())
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('schools', 'is_active')
