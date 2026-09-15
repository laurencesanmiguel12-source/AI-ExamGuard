"""Two gaps found by walking the whole program flow end to end against a throwaway school.

Everything else in that walk held: the approval gate, the one-current-year and one-active-term
invariants, duplicate refusals at every level, section ownership, roster inheritance and its
per-exam precedence, drop/reinstate, attempt limits, and all three delete guards. These are the
two places the flow let something through.
"""
from datetime import date, datetime, timedelta, timezone

import pytest
from fastapi import HTTPException

from app.schemas.exam import ExamCreate, ExamUpdate
from app.services.academic_service import AcademicService
from app.services.exam_service import ExamService


def _term(db, school_id, starts=date(2026, 6, 1), ends=date(2026, 10, 31), activate=True):
    year = AcademicService.create_year(
        "2026-2027", date(2026, 6, 1), date(2027, 5, 31), True, school_id, db
    )
    term = AcademicService.create_term(
        year.id, "1st Semester", 1, starts, ends, school_id, db
    )
    return AcademicService.set_term_status(term.id, "ACTIVE", school_id, db) if activate else term


def _exam_on(db, section, instructor, start, end, active=True):
    return ExamService.create(
        instructor.user,
        ExamCreate(
            title="Midterm", duration_minutes=30, total_points=10, passing_score=50,
            start_time=start, end_time=end, is_active=active, section_id=section.id,
        ),
        db,
    )


@pytest.fixture
def section(db, default_school, make_subject, make_instructor):
    term = _term(db, default_school.id)
    return AcademicService.create_section(
        make_subject(code="CS-101").id, term.id, make_instructor().id, "A",
        default_school.id, db,
    )


# --- closing a term must not strand an open exam ----------------------------------------------

def test_closing_a_term_with_an_open_exam_is_refused(db, default_school, section, make_student):
    """The gap. Closing marks every ENROLLED row COMPLETED and eligibility reads ENROLLED, so an
    exam whose window is still open would keep reporting is_active=True while admitting nobody -
    and reopening the term does NOT put the enrolments back, so it is not undoable either."""
    AcademicService.enroll(section.id, [make_student().id], default_school.id, db)
    now = datetime.now(timezone.utc)
    _exam_on(db, section, section.instructor, now - timedelta(hours=1), now + timedelta(days=2))

    with pytest.raises(HTTPException) as caught:
        AcademicService.set_term_status(section.term_id, "CLOSED", default_school.id, db)

    assert caught.value.status_code == 400
    assert "still open" in str(caught.value.detail)
    assert "Midterm" in str(caught.value.detail)


def test_the_refusal_names_what_to_do_about_it(db, default_school, section):
    now = datetime.now(timezone.utc)
    _exam_on(db, section, section.instructor, now - timedelta(hours=1), now + timedelta(days=2))

    with pytest.raises(HTTPException) as caught:
        AcademicService.set_term_status(section.term_id, "CLOSED", default_school.id, db)

    detail = str(caught.value.detail)
    assert "Deactivate" in detail
    assert "reopening it does not put them back" in detail


def test_an_inactive_exam_does_not_block_closing(db, default_school, section):
    """Only exams that could actually be sat. A draft nobody activated is not in anyone's way."""
    now = datetime.now(timezone.utc)
    _exam_on(db, section, section.instructor, now - timedelta(hours=1), now + timedelta(days=2),
             active=False)

    closed = AcademicService.set_term_status(section.term_id, "CLOSED", default_school.id, db)

    assert closed.status == "CLOSED"


def test_an_exam_whose_window_has_passed_does_not_block_closing(db, default_school, section):
    """The normal end-of-term case: every exam has been sat and the window is behind us."""
    now = datetime.now(timezone.utc)
    _exam_on(db, section, section.instructor, now - timedelta(days=5), now - timedelta(days=4))

    closed = AcademicService.set_term_status(section.term_id, "CLOSED", default_school.id, db)

    assert closed.status == "CLOSED"


def test_closing_still_completes_the_class_list_once_nothing_is_open(
    db, default_school, section, make_student
):
    """The behaviour the guard protects, not replaces."""
    student = make_student()
    AcademicService.enroll(section.id, [student.id], default_school.id, db)

    AcademicService.set_term_status(section.term_id, "CLOSED", default_school.id, db)

    roster = AcademicService.roster(section.id, default_school.id, db, active_only=False)
    assert [e.status for e in roster] == ["COMPLETED"]


# --- an exam has to overlap its own term -------------------------------------------------------

def test_an_exam_a_year_outside_its_term_is_refused(db, default_school, section):
    """Found in the walk: a term ending 2026-10-31 accepted an exam dated 2027-10-20. That exam
    then sits in the wrong term's reports forever and nothing says so."""
    start = datetime(2027, 10, 20, 9, tzinfo=timezone.utc)

    with pytest.raises(HTTPException) as caught:
        _exam_on(db, section, section.instructor, start, start + timedelta(hours=2))

    assert caught.value.status_code == 400
    assert "entirely outside" in str(caught.value.detail)
    assert "1st Semester" in str(caught.value.detail)


def test_an_exam_before_its_term_starts_is_refused(db, default_school, section):
    start = datetime(2025, 1, 5, 9, tzinfo=timezone.utc)

    with pytest.raises(HTTPException):
        _exam_on(db, section, section.instructor, start, start + timedelta(hours=2))


def test_a_makeup_running_just_past_the_term_end_is_allowed(db, default_school, section):
    """Deliberately an OVERLAP check, not containment. A deferred sitting a few days after the
    term ends is normal, and refusing it would push people to reopen a closed term to mark one
    paper."""
    start = datetime(2026, 10, 30, 9, tzinfo=timezone.utc)

    exam = _exam_on(db, section, section.instructor, start, start + timedelta(days=4))

    assert exam.id is not None


def test_moving_an_exams_dates_out_of_its_term_is_refused(db, default_school, section):
    """Checked on update too - shifting dates walks an exam out of its term as easily as picking
    the wrong section does."""
    now = datetime(2026, 7, 1, 9, tzinfo=timezone.utc)
    exam = _exam_on(db, section, section.instructor, now, now + timedelta(hours=2))

    with pytest.raises(HTTPException) as caught:
        ExamService.update(
            exam.id, section.instructor.user,
            ExamUpdate(start_time=datetime(2028, 1, 1, 9, tzinfo=timezone.utc),
                       end_time=datetime(2028, 1, 1, 11, tzinfo=timezone.utc)),
            db,
        )

    assert "entirely outside" in str(caught.value.detail)


def test_renaming_an_exam_does_not_re_trip_the_window_check(db, default_school, section):
    """The update path reads the stored dates when the body does not carry them - otherwise every
    unrelated edit would have to re-send a valid window."""
    now = datetime(2026, 7, 1, 9, tzinfo=timezone.utc)
    exam = _exam_on(db, section, section.instructor, now, now + timedelta(hours=2))

    updated = ExamService.update(
        exam.id, section.instructor.user, ExamUpdate(title="Renamed"), db
    )

    assert updated.title == "Renamed"


# --- a closed term stays closed ----------------------------------------------------------------

def test_an_exam_in_a_closed_term_cannot_be_re_activated(db, default_school, section):
    """The loophole the walk found. A closed term already refused new sections, new exams and new
    enrolment - but nothing stopped an EXISTING exam being switched back on inside one, and an
    explicit roster survives closure, so its students were still admitted."""
    now = datetime.now(timezone.utc)
    exam = _exam_on(db, section, section.instructor,
                    now - timedelta(days=5), now - timedelta(days=4), active=False)
    AcademicService.set_term_status(section.term_id, "CLOSED", default_school.id, db)

    with pytest.raises(HTTPException) as caught:
        ExamService.update(
            exam.id, section.instructor.user, ExamUpdate(is_active=True), db
        )

    assert caught.value.status_code == 400
    assert "closed" in str(caught.value.detail).lower()


def test_a_closed_term_refuses_the_sitting_itself(db, default_school, section, make_student):
    """The authoritative gate. The update check above is a courtesy - this is the one that holds
    however the exam came to be active, including rows already active when the term closed."""
    from app.models.exam_session import ExamSession  # noqa: F401
    from app.services.exam_session_service import ExamSessionService

    student = make_student()
    AcademicService.enroll(section.id, [student.id], default_school.id, db)
    now = datetime.now(timezone.utc)
    exam = _exam_on(db, section, section.instructor,
                    now - timedelta(days=5), now - timedelta(days=4), active=False)

    AcademicService.set_term_status(section.term_id, "CLOSED", default_school.id, db)
    # Straight to the column, the way an already-active row would have survived the close.
    exam.is_active = True
    exam.end_time = now + timedelta(hours=2)
    db.commit()

    with pytest.raises(HTTPException) as caught:
        ExamSessionService.start_exam(student, exam.id, db)

    assert caught.value.status_code == 403
    assert "closed" in str(caught.value.detail).lower()


def test_the_not_eligible_message_no_longer_blames_the_course(
    db, default_school, section, make_student
):
    """Eligibility has not been course-based since roster inheritance landed - it is section
    enrolment, or an explicit roster. "not available for your course" sent people to check the
    wrong thing."""
    from app.services.exam_session_service import ExamSessionService

    outsider = make_student()          # same school, not in this section
    now = datetime.now(timezone.utc)
    exam = _exam_on(db, section, section.instructor,
                    now - timedelta(hours=1), now + timedelta(hours=2))

    with pytest.raises(HTTPException) as caught:
        ExamSessionService.start_exam(outsider, exam.id, db)

    detail = str(caught.value.detail)
    assert "course" not in detail.lower()
    assert "enrolled in its class" in detail
