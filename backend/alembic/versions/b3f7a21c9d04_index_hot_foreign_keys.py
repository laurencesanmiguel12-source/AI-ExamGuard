"""Index the foreign keys the app actually filters and joins on

Postgres indexes a PRIMARY KEY and a UNIQUE constraint automatically. It does NOT index the
referencing side of a foreign key - that is left to the application - and 22 of this schema's 35
foreign keys had no index with the column in the leading position.

Only the hot ones are added here, "hot" meaning the column appears in a filter or join on a path
that runs per request rather than per administrative action. The rest (audit_logs.actor_user_id,
violations.appeal_reviewed_by, violations.training_reviewed_by, schools.reviewed_by_user_id,
student_answers.choice_id, student_answers.question_id, violations.question_id) are left alone:
each is read a handful of times on a screen somebody opens deliberately, and an unused index is
not free - it is maintained on every insert into tables that grow fastest.

**This changes nothing measurable on today's data.** The live database holds single-digit rows in
every table, and the planner will keep sequential-scanning them because that is genuinely cheaper.
The value is at the sizes this schema is built for: one row in `enrollments` per student per
class per term, one in `student_answers` per question per attempt, and one in `violations` per
flagged episode. `student_answers.exam_session_id` is the clearest case - grading reads every
answer for one session, and without an index that is a full scan of the largest table in the
schema, once per submitted exam.

Two groups are worth naming:

  * `users.school_id` and `users.role_id` are on the authentication path. Every authenticated
    request resolves a user and its role, and every school-scoped query in the app reaches school
    through a join that starts here.
  * `exams.subject_id`, `exams.section_id` and `exams.instructor_id` are the three ways an exam is
    reached. Roughly twenty call sites across auth, analytics, retention, risk scoring and
    near-miss capture join through one of them.

Created with the default (blocking) CREATE INDEX rather than CONCURRENTLY: these tables are small
today, the lock is momentary, and CONCURRENTLY cannot run inside the transaction Alembic wraps a
migration in. Revisit that if this is ever applied to a large live database.
"""
from typing import Sequence, Union

from alembic import op

revision: str = "b3f7a21c9d04"
down_revision: Union[str, Sequence[str], None] = "c8d40a91f5e2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# (index name, table, column) - named explicitly so the downgrade is exact rather than guessed.
INDEXES = [
    # authentication and school scoping, on every request
    ("ix_users_school_id", "users", "school_id"),
    ("ix_users_role_id", "users", "role_id"),
    ("ix_subjects_course_id", "subjects", "course_id"),
    ("ix_students_course_id", "students", "course_id"),
    # the three ways an exam is reached
    ("ix_exams_subject_id", "exams", "subject_id"),
    ("ix_exams_section_id", "exams", "section_id"),
    ("ix_exams_instructor_id", "exams", "instructor_id"),
    # loading an exam to sit it
    ("ix_questions_exam_id", "questions", "exam_id"),
    ("ix_choices_question_id", "choices", "question_id"),
    # grading: every answer for one session
    ("ix_student_answers_exam_session_id", "student_answers", "exam_session_id"),
    # who may sit this exam - both sides of the roster precedence rule
    ("ix_exam_rosters_student_id", "exam_rosters", "student_id"),
    ("ix_enrollments_student_id", "enrollments", "student_id"),
    # the academic hierarchy's own lists
    ("ix_sections_term_id", "sections", "term_id"),
    ("ix_sections_instructor_id", "sections", "instructor_id"),
    ("ix_instructor_subjects_subject_id", "instructor_subjects", "subject_id"),
]


def upgrade() -> None:
    for name, table, column in INDEXES:
        op.create_index(name, table, [column])


def downgrade() -> None:
    for name, table, _column in reversed(INDEXES):
        op.drop_index(name, table_name=table)
