"""add schools table and school_id scoping

Revision ID: 5b526f3a7f33
Revises: 83c62cecbf5c
Create Date: 2026-08-06 18:36:19.705879

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5b526f3a7f33'
down_revision: Union[str, Sequence[str], None] = '83c62cecbf5c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('schools',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('code', sa.String(length=20), nullable=False),
    sa.Column('name', sa.String(length=100), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('code')
    )

    # Columns start nullable so existing rows can be backfilled to one default school before the
    # NOT NULL constraint goes on - this app predates multi-tenancy, so every row that already
    # exists belongs to whichever single school it was actually running for.
    op.add_column('courses', sa.Column('school_id', sa.Integer(), nullable=True))
    op.add_column('users', sa.Column('school_id', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_courses_school_id', 'courses', 'schools', ['school_id'], ['id'])
    op.create_foreign_key('fk_users_school_id', 'users', 'schools', ['school_id'], ['id'])

    conn = op.get_bind()
    default_school_id = conn.execute(
        sa.text("INSERT INTO schools (code, name) VALUES ('DEFAULT', 'Arellano University') RETURNING id")
    ).scalar()
    conn.execute(sa.text("UPDATE courses SET school_id = :sid WHERE school_id IS NULL"), {"sid": default_school_id})
    conn.execute(sa.text("UPDATE users SET school_id = :sid WHERE school_id IS NULL"), {"sid": default_school_id})

    op.alter_column('courses', 'school_id', nullable=False)
    op.alter_column('users', 'school_id', nullable=False)

    op.drop_constraint(op.f('courses_code_key'), 'courses', type_='unique')
    op.create_unique_constraint('uq_course_school_code', 'courses', ['school_id', 'code'])
    op.drop_constraint(op.f('instructors_employee_number_key'), 'instructors', type_='unique')


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('fk_users_school_id', 'users', type_='foreignkey')
    op.drop_column('users', 'school_id')
    op.create_unique_constraint(op.f('instructors_employee_number_key'), 'instructors', ['employee_number'])
    op.drop_constraint('fk_courses_school_id', 'courses', type_='foreignkey')
    op.drop_constraint('uq_course_school_code', 'courses', type_='unique')
    op.create_unique_constraint(op.f('courses_code_key'), 'courses', ['code'])
    op.drop_column('courses', 'school_id')
    op.drop_table('schools')
