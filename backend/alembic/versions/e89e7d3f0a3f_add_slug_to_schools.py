"""add slug to schools

Revision ID: e89e7d3f0a3f
Revises: 5b526f3a7f33
Create Date: 2026-08-07 15:13:46.189432

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e89e7d3f0a3f'
down_revision: Union[str, Sequence[str], None] = '5b526f3a7f33'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Starts nullable so existing schools (pre-dating the slug column) can be backfilled from
    # their name before the NOT NULL constraint goes on.
    op.add_column('schools', sa.Column('slug', sa.String(length=150), nullable=True))

    conn = op.get_bind()
    # Postgres-native slugify: lowercase, non-alnum runs -> single hyphen, trim leading/trailing
    # hyphens - mirrors app/utils/slugify.py's Python logic for consistency.
    conn.execute(sa.text(
        "UPDATE schools SET slug = trim(both '-' from "
        "regexp_replace(lower(name), '[^a-z0-9]+', '-', 'g')) "
        "WHERE slug IS NULL"
    ))

    op.alter_column('schools', 'slug', nullable=False)
    op.create_unique_constraint('uq_schools_slug', 'schools', ['slug'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('uq_schools_slug', 'schools', type_='unique')
    op.drop_column('schools', 'slug')
