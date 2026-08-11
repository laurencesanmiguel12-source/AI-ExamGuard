"""seed default roles

Revision ID: 88a97c5b9b35
Revises: 2101e7fea16b
Create Date: 2026-08-11 05:37:45.943887

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '88a97c5b9b35'
down_revision: Union[str, Sequence[str], None] = '2101e7fea16b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Nothing seeded these before now - AuthService.create_user_account (school signup,
    # self-registration, admin-created instructor/student) looks roles up by name and 500s
    # ("<Role> role is not configured.") if the row doesn't exist. Only backend/tests/conftest.py
    # created them, so every real deploy's roles table was empty until now.
    # ON CONFLICT guards deployments that already have these rows from some prior manual seed.
    op.execute(
        sa.text(
            "INSERT INTO roles (name, created_at, updated_at) VALUES "
            "('admin', now(), now()), ('instructor', now(), now()), ('student', now(), now()) "
            "ON CONFLICT (name) DO NOTHING"
        )
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute(sa.text("DELETE FROM roles WHERE name IN ('admin', 'instructor', 'student')"))
