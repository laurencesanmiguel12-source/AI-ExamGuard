"""Add exams.section_id (nullable) and backfill every existing exam

Step 3 of the academic-hierarchy migration.

`section_id` is deliberately NULLABLE here and `subject_id` / `instructor_id` are left in place.
New code reads through the section; existing code keeps working off the direct links. Making the
column required and retiring the shortcuts is step 5, once nothing depends on them.

The backfill exploits a fact about the old schema: `instructor_subjects` IS the section list,
minus the term. Every existing exam already names a subject and an instructor, so the section it
belongs to can be reconstructed exactly - one section per distinct (subject, instructor) pair
actually used by an exam. Nothing is guessed.

Raw SQL rather than the ORM on purpose: a migration has to keep working when the models move on,
and importing them would couple this file to whatever those classes look like in a year's time.

Idempotent by construction - it only touches exams whose section_id IS NULL, and reuses any
section that already matches, so a partially applied run can be repeated safely.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a4f1c7e20b83"
down_revision: Union[str, Sequence[str], None] = "0b92bc10d860"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Section codes are per (subject, term). Backfilled sections take the first free letter rather
# than a marker like "LEGACY", because these are real classes that really ran - they just were
# not recorded as such.
_CODES = [chr(c) for c in range(ord("A"), ord("Z") + 1)]


def _backfill_term(conn, school_id: int) -> int:
    """The term backfilled sections belong to.

    Prefers a term the school has already set up - an ACTIVE one first, then any - so a school
    that has begun using the hierarchy keeps its own structure instead of gaining a stray parallel
    year. Only invents one when the school has nothing at all.
    """
    existing = conn.execute(sa.text("""
        SELECT t.id FROM terms t
        JOIN academic_years ay ON ay.id = t.academic_year_id
        WHERE ay.school_id = :school
        ORDER BY (t.status = 'ACTIVE') DESC, ay.starts_on DESC, t.sequence
        LIMIT 1
    """), {"school": school_id}).scalar()
    if existing is not None:
        return existing

    # Labelled so nobody mistakes it for a year somebody actually planned.
    year_id = conn.execute(sa.text("""
        INSERT INTO academic_years (school_id, label, starts_on, ends_on, is_current)
        VALUES (:school, 'Unrecorded (backfilled)', CURRENT_DATE, CURRENT_DATE + 365, TRUE)
        RETURNING id
    """), {"school": school_id}).scalar()

    # ACTIVE, not PLANNED: these exams already happened, and a PLANNED term would refuse the very
    # sections being created for them.
    return conn.execute(sa.text("""
        INSERT INTO terms (academic_year_id, name, sequence, starts_on, ends_on, status)
        VALUES (:year, 'Unrecorded term', 1, CURRENT_DATE, CURRENT_DATE + 365, 'ACTIVE')
        RETURNING id
    """), {"year": year_id}).scalar()


def _section_for(conn, subject_id: int, term_id: int, instructor_id: int) -> int:
    """Find the section for this (subject, term, instructor), creating it if absent."""
    found = conn.execute(sa.text("""
        SELECT id FROM sections
        WHERE subject_id = :subject AND term_id = :term AND instructor_id = :instructor
        LIMIT 1
    """), {"subject": subject_id, "term": term_id, "instructor": instructor_id}).scalar()
    if found is not None:
        return found

    taken = {
        row[0] for row in conn.execute(sa.text(
            "SELECT code FROM sections WHERE subject_id = :subject AND term_id = :term"
        ), {"subject": subject_id, "term": term_id})
    }
    code = next((c for c in _CODES if c not in taken), None)
    if code is None:
        # 26 sections of one subject in one term is not a real situation, but silently colliding
        # on the unique constraint would be worse than an obviously-generated name.
        code = f"S{len(taken) + 1}"

    return conn.execute(sa.text("""
        INSERT INTO sections (subject_id, term_id, instructor_id, code)
        VALUES (:subject, :term, :instructor, :code)
        RETURNING id
    """), {
        "subject": subject_id, "term": term_id,
        "instructor": instructor_id, "code": code,
    }).scalar()


def upgrade() -> None:
    op.add_column("exams", sa.Column("section_id", sa.Integer(), nullable=True))
    op.create_foreign_key("fk_exams_section_id", "exams", "sections", ["section_id"], ["id"])

    conn = op.get_bind()

    # An exam's school is reached through subject -> course, the same path the rest of the
    # codebase uses to scope subjects.
    pairs = conn.execute(sa.text("""
        SELECT DISTINCT c.school_id, e.subject_id, e.instructor_id
        FROM exams e
        JOIN subjects s ON s.id = e.subject_id
        JOIN courses  c ON c.id = s.course_id
        WHERE e.section_id IS NULL
    """)).fetchall()

    terms: dict[int, int] = {}
    for school_id, subject_id, instructor_id in pairs:
        if school_id not in terms:
            terms[school_id] = _backfill_term(conn, school_id)

        section_id = _section_for(conn, subject_id, terms[school_id], instructor_id)
        conn.execute(sa.text("""
            UPDATE exams SET section_id = :section
            WHERE section_id IS NULL
              AND subject_id = :subject
              AND instructor_id = :instructor
        """), {"section": section_id, "subject": subject_id, "instructor": instructor_id})


def downgrade() -> None:
    # Only the column goes. Sections created by the backfill are left in place deliberately: by
    # the time anyone downgrades, a real class list may have been enrolled against them, and
    # deleting that would destroy data this migration never created.
    op.drop_constraint("fk_exams_section_id", "exams", type_="foreignkey")
    op.drop_column("exams", "section_id")
