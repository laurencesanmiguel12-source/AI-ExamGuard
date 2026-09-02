"""add approval status to schools

Revision ID: c7f21a8d4e10
Revises: b4e1c0a97d32
Create Date: 2026-09-03 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c7f21a8d4e10'
down_revision: Union[str, Sequence[str], None] = 'b4e1c0a97d32'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # server_default='approved' is what backfills the schools that already exist - they are live
    # and in daily use, so they must not land in a pending queue and lock their users out at the
    # next login. New rows are created as 'pending' by the model default instead (SchoolService
    # sets it explicitly), so the server_default only ever applies to these pre-existing rows.
    op.add_column(
        'schools',
        sa.Column('status', sa.String(length=20), nullable=False, server_default='approved'),
    )
    op.add_column('schools', sa.Column('review_note', sa.String(length=255), nullable=True))
    op.add_column(
        'schools',
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column('schools', sa.Column('reviewed_by_user_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'fk_schools_reviewed_by_user_id', 'schools', 'users', ['reviewed_by_user_id'], ['id']
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Any school still pending or rejected becomes an ordinary school again - there is nowhere
    # else to record that state once the column is gone. is_active is left alone: a rejected
    # school that was never activated stays exactly as it was.
    op.drop_constraint('fk_schools_reviewed_by_user_id', 'schools', type_='foreignkey')
    op.drop_column('schools', 'reviewed_by_user_id')
    op.drop_column('schools', 'reviewed_at')
    op.drop_column('schools', 'review_note')
    op.drop_column('schools', 'status')
