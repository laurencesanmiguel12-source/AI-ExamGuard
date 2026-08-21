"""seed super admin role

Revision ID: 72a0926edfbf
Revises: ad5cb6fe6bab
Create Date: 2026-08-21 03:35:06.646156

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '72a0926edfbf'
down_revision: Union[str, Sequence[str], None] = 'ad5cb6fe6bab'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Platform-level role, distinct from the existing school-scoped "admin" - sees/manages every
    # school, not just its own. Same ON CONFLICT guard as 88a97c5b9b35's admin/instructor/student
    # seed, for the same reason (idempotent against a deploy that already has this row somehow).
    op.execute(
        sa.text(
            "INSERT INTO roles (name, created_at, updated_at) VALUES "
            "('super_admin', now(), now()) "
            "ON CONFLICT (name) DO NOTHING"
        )
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute(sa.text("DELETE FROM roles WHERE name = 'super_admin'"))
