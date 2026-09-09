"""The academic hierarchy: year -> term -> section -> enrolment.

Built in response to the defense panel asking for "a streamlined hierarchy for school year,
semester, course, subject and instructor". The framework's argument is that those are not five
separate fields but all downstream of one missing entity - a Section, being one offering of one
subject, in one term, taught by one instructor, to one enrolled group.

These tests pin the invariants that make the hierarchy trustworthy: exactly one current year, a
term state machine that actually refuses illegal moves, sections that cannot be assembled from
another school's parts, and enrolment that survives being re-run.
"""
from datetime import date, timedelta

import pytest
from fastapi import HTTPException

from app.models.enrollment import Enrollment
from app.services.academic_service import AcademicService

JUN = date(2026, 6, 1)
OCT = date(2026, 10, 31)
NOV = date(2026, 11, 1)
MAR = date(2027, 3, 31)


def make_year(db, school_id, label="2026-2027", current=False):
    return AcademicService.create_year(label, JUN, date(2027, 5, 31), current, school_id, db)


def make_term(db, school_id, year, name="1st Semester", sequence=1, starts=JUN, ends=OCT):
    return AcademicService.create_term(year.id, name, sequence, starts, ends, school_id, db)


# --- academic years ---------------------------------------------------------------------------

def test_the_first_year_becomes_current_even_if_not_asked(db, default_school):
    """A school with years defined but none current would make every "current term" view
    silently empty, which looks like data loss rather than a missing setting."""
    year = make_year(db, default_school.id, current=False)

    assert year.is_current is True


def test_only_one_year_can_be_current(db, default_school):
    first = make_year(db, default_school.id, label="2025-2026")
    second = make_year(db, default_school.id, label="2026-2027", current=True)

    db.refresh(first)
    assert second.is_current is True
    assert first.is_current is False
    assert AcademicService.current_year(default_school.id, db).id == second.id


def test_a_year_must_end_after_it_starts(db, default_school):
    with pytest.raises(HTTPException) as caught:
        AcademicService.create_year("Backwards", date(2027, 1, 1), date(2026, 1, 1),
                                    False, default_school.id, db)
    assert caught.value.status_code == 400


def test_one_school_cannot_define_the_same_year_twice(db, default_school):
    make_year(db, default_school.id, label="2026-2027")

    with pytest.raises(HTTPException) as caught:
        make_year(db, default_school.id, label="2026-2027")
    assert "already exists" in str(caught.value.detail)


def test_two_schools_may_both_run_the_same_year(db, default_school, make_school):
    other = make_school()
    make_year(db, default_school.id, label="2026-2027")

    # Not a clash - the label is unique per school, not globally.
    assert make_year(db, other.id, label="2026-2027").id is not None


def test_years_are_scoped_to_their_school(db, default_school, make_school):
    other = make_school()
    make_year(db, default_school.id, label="2026-2027")
    make_year(db, other.id, label="2026-2027")

    assert len(AcademicService.list_years(default_school.id, db)) == 1


# --- terms ------------------------------------------------------------------------------------

def test_a_term_starts_planned_not_running(db, default_school):
    """Setting up next term must not disturb the one currently being taught."""
    year = make_year(db, default_school.id)
    assert make_term(db, default_school.id, year).status == "PLANNED"


def test_two_terms_cannot_occupy_the_same_position(db, default_school):
    year = make_year(db, default_school.id)
    make_term(db, default_school.id, year, "1st Semester", 1)

    with pytest.raises(HTTPException) as caught:
        make_term(db, default_school.id, year, "Something else", 1)
    assert "position 1" in str(caught.value.detail)


def test_a_term_moves_planned_to_active_to_closed(db, default_school):
    year = make_year(db, default_school.id)
    term = make_term(db, default_school.id, year)

    assert AcademicService.set_term_status(term.id, "ACTIVE", default_school.id, db).status == "ACTIVE"
    assert AcademicService.set_term_status(term.id, "CLOSED", default_school.id, db).status == "CLOSED"


def test_a_planned_term_cannot_jump_straight_to_closed(db, default_school):
    year = make_year(db, default_school.id)
    term = make_term(db, default_school.id, year)

    with pytest.raises(HTTPException) as caught:
        AcademicService.set_term_status(term.id, "CLOSED", default_school.id, db)
    assert "cannot become" in str(caught.value.detail)


def test_a_closed_term_can_be_reopened(db, default_school):
    """A term closed by mistake, or reopened for a deferred sitting, is a real situation -
    refusing it would push someone to edit the database by hand."""
    year = make_year(db, default_school.id)
    term = make_term(db, default_school.id, year)
    AcademicService.set_term_status(term.id, "ACTIVE", default_school.id, db)
    AcademicService.set_term_status(term.id, "CLOSED", default_school.id, db)

    assert AcademicService.set_term_status(term.id, "ACTIVE", default_school.id, db).status == "ACTIVE"


def test_only_one_term_runs_at_a_time(db, default_school):
    year = make_year(db, default_school.id)
    first = make_term(db, default_school.id, year, "1st Semester", 1)
    second = make_term(db, default_school.id, year, "2nd Semester", 2, NOV, MAR)
    AcademicService.set_term_status(first.id, "ACTIVE", default_school.id, db)

    with pytest.raises(HTTPException) as caught:
        AcademicService.set_term_status(second.id, "ACTIVE", default_school.id, db)
    # Deliberately refused rather than auto-closing the running one, which would silently end a
    # term somebody is still teaching.
    assert "still active" in str(caught.value.detail)


def test_current_term_is_the_active_one_in_the_current_year(db, default_school):
    year = make_year(db, default_school.id)
    term = make_term(db, default_school.id, year)
    AcademicService.set_term_status(term.id, "ACTIVE", default_school.id, db)

    assert AcademicService.current_term(default_school.id, db).id == term.id


def test_no_active_term_returns_none_rather_than_guessing(db, default_school):
    year = make_year(db, default_school.id)
    make_term(db, default_school.id, year)

    # A caller showing "no current term, open one" beats one silently showing last year's data.
    assert AcademicService.current_term(default_school.id, db) is None


def test_a_term_from_another_school_is_not_reachable(db, default_school, make_school):
    other = make_school()
    year = make_year(db, other.id)
    term = make_term(db, other.id, year)

    with pytest.raises(HTTPException) as caught:
        AcademicService.get_term(term.id, default_school.id, db)
    assert caught.value.status_code == 404


# --- sections ---------------------------------------------------------------------------------

def _active_term(db, school_id):
    year = make_year(db, school_id)
    term = make_term(db, school_id, year)
    AcademicService.set_term_status(term.id, "ACTIVE", school_id, db)
    return term


def test_a_section_ties_subject_term_and_instructor_together(
    db, default_school, make_subject, make_instructor
):
    term = _active_term(db, default_school.id)
    subject = make_subject(code="CS-101")
    instructor = make_instructor()

    section = AcademicService.create_section(
        subject.id, term.id, instructor.id, "A", default_school.id, db
    )

    assert (section.subject_id, section.term_id, section.instructor_id) == (
        subject.id, term.id, instructor.id
    )
    assert section.label == "CS-101 A"


def test_two_instructors_can_each_own_a_section_of_one_subject(
    db, default_school, make_subject, make_instructor
):
    """The panel's core complaint, now representable: same subject, same term, different classes
    with different teachers - and no ambiguity about which is whose."""
    term = _active_term(db, default_school.id)
    subject = make_subject(code="CS-101")
    first = make_instructor()
    second = make_instructor()

    a = AcademicService.create_section(subject.id, term.id, first.id, "A", default_school.id, db)
    b = AcademicService.create_section(subject.id, term.id, second.id, "B", default_school.id, db)

    assert a.instructor_id != b.instructor_id
    assert {a.label, b.label} == {"CS-101 A", "CS-101 B"}


def test_the_same_section_code_cannot_repeat_within_a_term(
    db, default_school, make_subject, make_instructor
):
    term = _active_term(db, default_school.id)
    subject = make_subject(code="CS-101")
    instructor = make_instructor()
    AcademicService.create_section(subject.id, term.id, instructor.id, "A", default_school.id, db)

    with pytest.raises(HTTPException) as caught:
        AcademicService.create_section(subject.id, term.id, instructor.id, "A", default_school.id, db)
    assert "already exists" in str(caught.value.detail)


def test_the_same_section_code_may_repeat_next_term(
    db, default_school, make_subject, make_instructor
):
    year = make_year(db, default_school.id)
    first = make_term(db, default_school.id, year, "1st Semester", 1)
    second = make_term(db, default_school.id, year, "2nd Semester", 2, NOV, MAR)
    subject = make_subject(code="CS-101")
    instructor = make_instructor()

    AcademicService.create_section(subject.id, first.id, instructor.id, "A", default_school.id, db)
    # "CS-101 A" runs again next semester - that is normal, not a duplicate.
    assert AcademicService.create_section(
        subject.id, second.id, instructor.id, "A", default_school.id, db
    ).id is not None


def test_a_closed_term_accepts_no_new_sections(db, default_school, make_subject, make_instructor):
    year = make_year(db, default_school.id)
    term = make_term(db, default_school.id, year)
    AcademicService.set_term_status(term.id, "ACTIVE", default_school.id, db)
    AcademicService.set_term_status(term.id, "CLOSED", default_school.id, db)

    with pytest.raises(HTTPException) as caught:
        AcademicService.create_section(
            make_subject().id, term.id, make_instructor().id, "A", default_school.id, db
        )
    assert "closed" in str(caught.value.detail).lower()


def test_another_schools_subject_cannot_be_attached_to_this_terms_section(
    db, default_school, make_school, make_course, make_subject, make_instructor
):
    """Ids existing is not permission to use them - the same cross-tenant guard the rest of the
    codebase applies."""
    term = _active_term(db, default_school.id)
    other = make_school()
    foreign_subject = make_subject(course=make_course(school=other))

    with pytest.raises(HTTPException) as caught:
        AcademicService.create_section(
            foreign_subject.id, term.id, make_instructor().id, "A", default_school.id, db
        )
    assert caught.value.status_code == 404


# --- enrolment --------------------------------------------------------------------------------

def _section(db, school_id, make_subject, make_instructor):
    term = _active_term(db, school_id)
    return AcademicService.create_section(
        make_subject().id, term.id, make_instructor().id, "A", school_id, db
    )


def test_enrolling_students_builds_the_class_list(
    db, default_school, make_subject, make_instructor, make_student
):
    section = _section(db, default_school.id, make_subject, make_instructor)
    students = [make_student(), make_student(), make_student()]

    result = AcademicService.enroll(
        section.id, [s.id for s in students], default_school.id, db
    )

    assert result["enrolled"] == 3
    assert len(AcademicService.roster(section.id, default_school.id, db)) == 3


def test_re_running_the_same_enrolment_is_safe(
    db, default_school, make_subject, make_instructor, make_student
):
    """Re-uploading an edited class list must add the new names, not produce a wall of duplicate
    errors."""
    section = _section(db, default_school.id, make_subject, make_instructor)
    first, second = make_student(), make_student()
    AcademicService.enroll(section.id, [first.id], default_school.id, db)

    result = AcademicService.enroll(section.id, [first.id, second.id], default_school.id, db)

    assert result["enrolled"] == 1
    assert result["skipped_already_enrolled"] == 1
    assert result["errors"] == []


def test_a_dropped_student_is_reinstated_rather_than_rejected(
    db, default_school, make_subject, make_instructor, make_student
):
    section = _section(db, default_school.id, make_subject, make_instructor)
    student = make_student()
    AcademicService.enroll(section.id, [student.id], default_school.id, db)
    AcademicService.set_enrollment_status(section.id, student.id, "DROPPED", default_school.id, db)

    result = AcademicService.enroll(section.id, [student.id], default_school.id, db)

    assert result["reinstated"] == 1
    assert len(AcademicService.roster(section.id, default_school.id, db)) == 1


def test_a_dropped_student_leaves_the_roster_but_keeps_their_row(
    db, default_school, make_subject, make_instructor, make_student
):
    """The row is what gives their existing attempts and violations a coherent context - deleting
    it would orphan that history."""
    section = _section(db, default_school.id, make_subject, make_instructor)
    student = make_student()
    AcademicService.enroll(section.id, [student.id], default_school.id, db)

    AcademicService.set_enrollment_status(section.id, student.id, "DROPPED", default_school.id, db)

    assert AcademicService.roster(section.id, default_school.id, db) == []
    assert len(AcademicService.roster(section.id, default_school.id, db, active_only=False)) == 1


def test_another_schools_student_cannot_be_enrolled(
    db, default_school, make_school, make_course, make_subject, make_instructor,
    make_student, make_user
):
    section = _section(db, default_school.id, make_subject, make_instructor)
    other = make_school()
    # A student belongs to the school on their USER row - that is how every other query in the
    # codebase scopes students, so a foreign student needs a foreign user, not just a course
    # that happens to sit in another school.
    foreign = make_student(
        user=make_user("student", school=other),
        course=make_course(school=other),
    )

    result = AcademicService.enroll(section.id, [foreign.id], default_school.id, db)

    assert result["enrolled"] == 0
    assert "not in this school" in result["errors"][0]


def test_one_bad_student_does_not_abandon_the_rest_of_an_enrolment(
    db, default_school, make_school, make_course, make_instructor, make_subject,
    make_student, make_user
):
    """A class list with one stale id in it should still enrol everybody else."""
    section = _section(db, default_school.id, make_subject, make_instructor)
    good = make_student()
    foreign = make_student(
        user=make_user("student", school=make_school()),
        course=make_course(school=make_school()),
    )

    result = AcademicService.enroll(section.id, [good.id, foreign.id], default_school.id, db)

    assert result["enrolled"] == 1
    assert len(result["errors"]) == 1


def test_closing_a_term_completes_its_enrolments(
    db, default_school, make_subject, make_instructor, make_student
):
    """Otherwise last term's class lists keep looking current forever."""
    section = _section(db, default_school.id, make_subject, make_instructor)
    student = make_student()
    AcademicService.enroll(section.id, [student.id], default_school.id, db)

    AcademicService.set_term_status(section.term_id, "CLOSED", default_school.id, db)

    remaining = db.query(Enrollment).filter(Enrollment.section_id == section.id).all()
    assert [e.status for e in remaining] == ["COMPLETED"]


def test_a_closed_term_accepts_no_new_enrolment(
    db, default_school, make_subject, make_instructor, make_student
):
    section = _section(db, default_school.id, make_subject, make_instructor)
    AcademicService.set_term_status(section.term_id, "CLOSED", default_school.id, db)

    with pytest.raises(HTTPException) as caught:
        AcademicService.enroll(section.id, [make_student().id], default_school.id, db)
    assert "closed" in str(caught.value.detail).lower()


def test_sections_can_be_listed_for_one_instructor(
    db, default_school, make_subject, make_instructor
):
    """What an instructor's own dashboard will scope to - their classes this term, rather than
    today's approximation via subject assignment."""
    term = _active_term(db, default_school.id)
    mine, theirs = make_instructor(), make_instructor()
    AcademicService.create_section(make_subject().id, term.id, mine.id, "A", default_school.id, db)
    AcademicService.create_section(make_subject().id, term.id, theirs.id, "A", default_school.id, db)

    found = AcademicService.list_sections(default_school.id, db, instructor_id=mine.id)

    assert len(found) == 1
    assert found[0].instructor_id == mine.id
