"""An exam's roster inherited from its section's class list.

Step 4 of the academic-hierarchy migration, and the highest-risk one. Since 2026-08-20 an exam
with an empty roster admits NOBODY - a deliberate policy flip, not a bug. Combine that policy with
inheritance carelessly and you get the worst possible outcome: an exam that looks correctly
configured, points at a real section, and silently locks out its entire class on exam day.

These tests pin both halves - that inheritance works, and that it never quietly widens or narrows
who may sit an exam.
"""
from datetime import date, datetime, timedelta, timezone

import pytest

from app.models.exam_roster import ExamRoster
from app.services.academic_service import AcademicService
from app.services.exam_service import ExamService


def _term(db, school_id):
    year = AcademicService.create_year(
        "2026-2027", date(2026, 6, 1), date(2027, 5, 31), True, school_id, db
    )
    term = AcademicService.create_term(
        year.id, "1st Semester", 1, date(2026, 6, 1), date(2026, 10, 31), school_id, db
    )
    return AcademicService.set_term_status(term.id, "ACTIVE", school_id, db)


def _exam_on_section(db, school_id, make_exam, make_subject, make_instructor):
    """An exam wired to a section, the way step 3 leaves them."""
    term = _term(db, school_id)
    subject = make_subject(code="CS-101")
    instructor = make_instructor()
    section = AcademicService.create_section(
        subject.id, term.id, instructor.id, "A", school_id, db
    )
    # Handed to the fixture rather than assigned afterwards: since step 5 an exam cannot exist
    # without a section, so make_exam would otherwise build a second one just to have it replaced
    # - and that spare section would bring its own academic year with it.
    exam = make_exam(subject=subject, instructor=instructor, section=section)
    return exam, section


# --- inheritance ------------------------------------------------------------------------------

def test_a_section_enrolled_student_may_sit_the_exam_with_no_roster_typed_in(
    db, default_school, make_exam, make_subject, make_instructor, make_student
):
    """The normal case, and the reason this exists: a roster no longer has to be built by hand
    for every single exam."""
    exam, section = _exam_on_section(db, default_school.id, make_exam, make_subject, make_instructor)
    student = make_student(course=exam.subject.course)
    AcademicService.enroll(section.id, [student.id], default_school.id, db)

    assert ExamService.is_student_eligible(student, exam, db) is True


def test_a_student_not_in_the_section_may_not(
    db, default_school, make_exam, make_subject, make_instructor, make_student
):
    exam, _section = _exam_on_section(db, default_school.id, make_exam, make_subject, make_instructor)
    outsider = make_student(course=exam.subject.course)

    assert ExamService.is_student_eligible(outsider, exam, db) is False


def test_a_dropped_student_loses_eligibility(
    db, default_school, make_exam, make_subject, make_instructor, make_student
):
    exam, section = _exam_on_section(db, default_school.id, make_exam, make_subject, make_instructor)
    student = make_student(course=exam.subject.course)
    AcademicService.enroll(section.id, [student.id], default_school.id, db)

    AcademicService.set_enrollment_status(section.id, student.id, "DROPPED", default_school.id, db)

    assert ExamService.is_student_eligible(student, exam, db) is False


def test_a_cross_programme_student_enrolled_in_the_section_is_eligible(
    db, default_school, make_exam, make_subject, make_instructor, make_student, make_course
):
    """Enrolling someone in a section names that exact student - a stronger statement than
    "belongs to the same programme". Electives and cross-enrolment are normal, and requiring both
    would reject a student from an exam they were deliberately enrolled for."""
    exam, section = _exam_on_section(db, default_school.id, make_exam, make_subject, make_instructor)
    other_programme = make_student(course=make_course(code="BSIT"))
    AcademicService.enroll(section.id, [other_programme.id], default_school.id, db)

    assert ExamService.is_student_eligible(other_programme, exam, db) is True


# --- explicit roster still wins -----------------------------------------------------------------

def test_an_explicit_roster_overrides_the_class_list(
    db, default_school, make_exam, make_subject, make_instructor, make_student
):
    """A makeup sitting for two students must not admit the other forty."""
    exam, section = _exam_on_section(db, default_school.id, make_exam, make_subject, make_instructor)
    picked = make_student(course=exam.subject.course)
    classmate = make_student(course=exam.subject.course)
    AcademicService.enroll(section.id, [picked.id, classmate.id], default_school.id, db)

    db.add(ExamRoster(exam_id=exam.id, student_id=picked.id))
    db.commit()

    assert ExamService.is_student_eligible(picked, exam, db) is True
    # Enrolled in the section, but deliberately not in this sitting.
    assert ExamService.is_student_eligible(classmate, exam, db) is False


def test_any_explicit_row_switches_the_whole_exam_to_explicit_mode(
    db, default_school, make_exam, make_subject, make_instructor, make_student
):
    """Checked per-exam, not per-student. Were it per-student, every classmate without a row
    would fall through to inheritance and be admitted anyway - which is the exact bug this
    ordering avoids."""
    exam, section = _exam_on_section(db, default_school.id, make_exam, make_subject, make_instructor)
    picked = make_student(course=exam.subject.course)
    AcademicService.enroll(section.id, [picked.id], default_school.id, db)

    assert ExamService.roster_source(exam, db)["source"] == "SECTION"
    db.add(ExamRoster(exam_id=exam.id, student_id=picked.id))
    db.commit()
    assert ExamService.roster_source(exam, db)["source"] == "EXPLICIT"


def test_the_old_explicit_only_behaviour_is_unchanged(
    db, default_school, make_exam, make_student
):
    """An explicitly rostered student behaves exactly as before inheritance existed.

    The "no section at all" half of this test went with step 5 - that shape is now refused by the
    schema, and its own test is below.
    """
    exam = make_exam()
    student = make_student(course=exam.subject.course, exam=exam)

    assert ExamService.is_student_eligible(student, exam, db) is True


def test_course_membership_still_gates_the_explicit_path(
    db, default_school, make_exam, make_student, make_course
):
    """The safety net for a hand-built list, where a mistyped id is a real possibility."""
    exam = make_exam()
    wrong_programme = make_student(course=make_course(code="BSIT"))
    db.add(ExamRoster(exam_id=exam.id, student_id=wrong_programme.id))
    db.commit()

    assert ExamService.is_student_eligible(wrong_programme, exam, db) is False


# --- the lockout hazard --------------------------------------------------------------------------

def test_neither_source_still_admits_nobody(
    db, default_school, make_exam, make_student
):
    """The 2026-08-20 policy, preserved exactly. Deliberately NOT "no roster means course-wide".

    A student in the exam's course, not rostered by hand and not enrolled in its section, is not
    eligible - being in the programme has never been enough on its own.
    """
    exam = make_exam()
    student = make_student(course=exam.subject.course)

    assert ExamService.is_student_eligible(student, exam, db) is False


def test_an_empty_section_locks_everyone_out_and_says_so(
    db, default_school, make_exam, make_subject, make_instructor, make_student
):
    """THE hazard of this migration. An exam pointing at a real section with nobody enrolled looks
    correctly configured and admits no one. The behaviour is correct - it must not silently invent
    a roster - so the requirement is that it is REPORTED, not that it is prevented."""
    exam, _section = _exam_on_section(db, default_school.id, make_exam, make_subject, make_instructor)
    student = make_student(course=exam.subject.course)

    assert ExamService.is_student_eligible(student, exam, db) is False

    source = ExamService.roster_source(exam, db)
    assert source["source"] == "SECTION"
    assert source["count"] == 0
    assert source["admits_nobody"] is True, "an empty inherited roster must be visible, not silent"


def test_roster_source_reports_the_inherited_headcount(
    db, default_school, make_exam, make_subject, make_instructor, make_student
):
    exam, section = _exam_on_section(db, default_school.id, make_exam, make_subject, make_instructor)
    AcademicService.enroll(
        section.id, [make_student(course=exam.subject.course).id for _ in range(3)],
        default_school.id, db,
    )

    source = ExamService.roster_source(exam, db)

    assert (source["source"], source["count"], source["admits_nobody"]) == ("SECTION", 3, False)


def test_an_exam_cannot_exist_without_a_section(db, default_school, make_subject, make_instructor):
    """Step 5's guarantee, enforced by the database rather than by convention.

    roster_source still has a "NONE" branch for an exam with no section; this is what makes that
    branch unreachable in practice, and it belongs in the schema rather than in a code review.
    """
    from sqlalchemy.exc import IntegrityError

    from app.models.exam import Exam

    subject = make_subject()
    instructor = make_instructor()
    now = datetime.now(timezone.utc)

    # A SAVEPOINT rather than a plain flush: the failed insert has to be unwound without taking
    # the surrounding per-test transaction with it (see the `db` fixture).
    with pytest.raises(IntegrityError):
        with db.begin_nested():
            db.add(Exam(
                title="Sectionless", duration_minutes=30, total_points=0, passing_score=50,
                start_time=now, end_time=now + timedelta(hours=1),
                subject_id=subject.id, instructor_id=instructor.id,
            ))
            db.flush()


def test_starting_an_exam_uses_the_inherited_roster_end_to_end(
    db, default_school, make_exam, make_subject, make_instructor, make_student
):
    """The whole chain: enrolled in the section, never rostered by hand, still able to sit it."""
    from app.services.exam_session_service import ExamSessionService

    exam, section = _exam_on_section(db, default_school.id, make_exam, make_subject, make_instructor)
    exam.is_active = True
    exam.end_time = datetime.now(timezone.utc) + timedelta(hours=2)
    db.commit()
    student = make_student(course=exam.subject.course)
    AcademicService.enroll(section.id, [student.id], default_school.id, db)

    session = ExamSessionService.start_exam(student, exam.id, db)

    assert session.status == "IN_PROGRESS"
