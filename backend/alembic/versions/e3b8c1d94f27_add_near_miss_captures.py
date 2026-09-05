"""add near_miss_captures

Revision ID: e3b8c1d94f27
Revises: c7f21a8d4e10
Create Date: 2026-09-05 09:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e3b8c1d94f27'
down_revision: Union[str, Sequence[str], None] = 'c7f21a8d4e10'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Frames the phone detector scored as plausible but did not act on. Kept out of the violations
    # table on purpose - a near miss is not a violation, and six services read
    # Violation.event_type. See app/models/near_miss_capture.py for the full reasoning.
    op.create_table(
        'near_miss_captures',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('exam_session_id', sa.Integer(), nullable=False),
        sa.Column('detector', sa.String(length=30), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=False),
        sa.Column('evidence_path', sa.String(length=255), nullable=True),
        sa.Column('training_review_status', sa.String(length=20), nullable=False,
                  server_default='PENDING'),
        sa.Column('training_exported_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'),
                  nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'),
                  nullable=False),
        sa.ForeignKeyConstraint(['exam_session_id'], ['exam_sessions.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_near_miss_captures_exam_session_id'),
        'near_miss_captures', ['exam_session_id'], unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Captured frames on disk are NOT removed here - dropping a table should not silently delete
    # image files that a re-upgrade could no longer account for. Clear
    # backend/storage/near_miss_evidence/ by hand if the rollback is permanent.
    op.drop_index(op.f('ix_near_miss_captures_exam_session_id'), table_name='near_miss_captures')
    op.drop_table('near_miss_captures')
