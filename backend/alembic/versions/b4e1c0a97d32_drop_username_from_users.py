"""drop username from users

Revision ID: b4e1c0a97d32
Revises: 0a75dc28ca83
Create Date: 2026-09-01 20:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b4e1c0a97d32'
down_revision: Union[str, Sequence[str], None] = '0a75dc28ca83'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # username was globally unique across every school while nothing ever read it - login and
    # every user lookup key on email. Its only live effect was rejecting registrations with
    # "Username already exists." when an unrelated school had taken the name, which is why
    # instructors were finding students missing from their rosters: those students had never
    # successfully registered. Dropping the column drops its unique constraint with it.
    op.drop_column('users', 'username')


def downgrade() -> None:
    """Downgrade schema."""
    # Backfill from email (already unique and NOT NULL) so the re-added NOT NULL + UNIQUE
    # constraints hold on a table that has rows. The original values are not recoverable.
    op.add_column('users', sa.Column('username', sa.String(length=50), nullable=True))
    op.execute("UPDATE users SET username = left(email, 50)")
    op.alter_column('users', 'username', nullable=False)
    op.create_unique_constraint('users_username_key', 'users', ['username'])
