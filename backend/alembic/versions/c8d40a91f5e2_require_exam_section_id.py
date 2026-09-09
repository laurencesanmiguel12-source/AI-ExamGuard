"""Make exams.section_id NOT NULL

Step 5 of the academic-hierarchy migration: a section stops being an optional extra on an exam and
becomes the thing an exam is filed under.

Step 3 backfilled every exam that existed at the time, but the exam form was never taught to send
a section, so **every exam created through the UI between step 3 and now has section_id NULL**.
This migration therefore has to sweep for stragglers before it can add the constraint - a plain
ALTER would fail on the live database, and failing there is the worst place to find out.

The sweep is the same reconstruction step 3 used, repeated rather than imported: a migration has
to keep working when other files move on, and reaching into another revision module for helpers
couples this one to whatever that file looks like in a year's time. `instructor_subjects` IS the
section list minus the term, and every exam already names a subject and an instructor, so the
section it belongs to is reconstructable exactly. Nothing is guessed.

Idempotent by construction - only exams whose section_id IS NULL are touched, and any section that
already matches is reused rather than duplicated.

The downgrade drops the NOT NULL only. It does not unpick the backfill: by then real class lists
may be enrolled against those sections, and deleting them would destroy data this migration never
created.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c8d40a91f5e2"
down_revision: Union[str, Sequence[str], None] = "a4f1c7e20b83"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_CODES = [chr(c) for c in range(ord("A"), ord("Z") + 1)]


def _backfill_term(conn, school_id: int) -> int:
    """The term a reconstructed section belongs to.

    Prefers a term the school has already set up - ACTIVE first, then any - so a school that has
    begun using the hierarchy keeps its own structure instead of gaining a stray parallel year.
    Only invents one when the school has nothing at all.
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

    year_id = conn.execute(sa.text("""
        INSERT INTO academic_years (school_id, label, starts_on, ends_on, is_current)
        VALUES (:school, 'Unrecorded (backfilled)', CURRENT_DATE, CURRENT_DATE + 365, TRUE)
        RETURNING id
    """), {"school": school_id}).scalar()

    # ACTIVE rather than PLANNED: these exams already exist, and exam creation refuses a closed
    # term - leaving them parented to something that reads as not-yet-running would be a lie.
    return conn.execute(sa.text("""
        INSERT INTO terms (academic_year_id, name, sequence, starts_on, ends_on, status)
        VALUES (:year, 'Unrecorded term', 1, CURRENT_DATE, CURRENT_DATE + 365, 'ACTIVE')
        RETURNING id
    """), {"year": year_id}).scalar()


def _section_for(conn, subject_id: int, term_id: int, instructor_id: int) -> int:
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
    conn = op.get_bind()

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

    # Anything still NULL here has no subject or no course to reach a school through, so the sweep
    # above could not see it - a row the schema should not have allowed. Refuse loudly rather than
    # let ALTER fail with a constraint error that says nothing about which exam is wrong.
    orphans = conn.execute(sa.text(
        "SELECT id, title FROM exams WHERE section_id IS NULL"
    )).fetchall()
    if orphans:
        listed = ", ".join(f"#{i} {t!r}" for i, t in orphans)
        raise RuntimeError(
            "Cannot require exams.section_id: these exams have no subject/course to reconstruct "
            f"a section from, so they must be fixed or deleted by hand first: {listed}"
        )

    op.alter_column("exams", "section_id", existing_type=sa.Integer(), nullable=False)


def downgrade() -> None:
    op.alter_column("exams", "section_id", existing_type=sa.Integer(), nullable=True)
