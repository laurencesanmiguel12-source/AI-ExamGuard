"""The exam due date as an actual gate.

`exam.end_time` has existed on the model, the create form and the API response since the
beginning, but ExamSessionService.start_exam never read it - it checked is_active, eligibility
and face enrolment only. So a deadline was a label, and an exam stayed startable indefinitely
until someone remembered to flip is_active by hand.

The boundary these tests pin down is *beginning* versus *finishing*: the deadline governs when a
student may start, and deliberately does not touch a session already in progress.
"""
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import HTTPException

from app.models.exam_session import ExamSession
from app.services.exam_session_service import ExamSessionService


def _start(student, exam, db):
    return ExamSessionService.start_exam(student, exam.id, db)


def test_cannot_start_an_exam_whose_deadline_has_passed(db, make_student, make_exam):
    exam = make_exam(end_time=datetime.now(timezone.utc) - timedelta(hours=2), is_active=True)
    student = make_student(course=exam.subject.course, exam=exam)

    with pytest.raises(HTTPException) as caught:
        _start(student, exam, db)

    assert caught.value.status_code == 400
    assert "closed" in str(caught.value.detail).lower()
    assert db.query(ExamSession).filter(ExamSession.exam_id == exam.id).count() == 0


def test_the_message_names_the_date_so_a_student_can_check_it(db, make_student, make_exam):
    closed_at = datetime.now(timezone.utc) - timedelta(days=3)
    exam = make_exam(end_time=closed_at, is_active=True)
    student = make_student(course=exam.subject.course, exam=exam)

    with pytest.raises(HTTPException) as caught:
        _start(student, exam, db)

    # "This exam is closed" with no date leaves them unable to tell whether they misread the
    # deadline or the instructor moved it.
    assert closed_at.strftime("%d %b %Y") in str(caught.value.detail)


def test_being_left_active_no_longer_keeps_a_closed_exam_open(db, make_student, make_exam):
    """The whole point: is_active was the only gate, so forgetting to deactivate meant the
    deadline did nothing at all."""
    exam = make_exam(end_time=datetime.now(timezone.utc) - timedelta(minutes=1), is_active=True)
    student = make_student(course=exam.subject.course, exam=exam)

    with pytest.raises(HTTPException):
        _start(student, exam, db)


def test_an_exam_still_within_its_window_starts_normally(db, make_student, make_exam):
    exam = make_exam(end_time=datetime.now(timezone.utc) + timedelta(hours=1), is_active=True)
    student = make_student(course=exam.subject.course, exam=exam)

    session = _start(student, exam, db)

    assert session.status == "IN_PROGRESS"


def test_a_deadline_seconds_away_still_lets_a_student_begin(db, make_student, make_exam):
    """Only a *passed* deadline blocks. Rounding a student out early would be the wrong
    direction to be wrong in."""
    exam = make_exam(end_time=datetime.now(timezone.utc) + timedelta(seconds=30), is_active=True)
    student = make_student(course=exam.subject.course, exam=exam)

    assert _start(student, exam, db).status == "IN_PROGRESS"


def test_a_session_already_in_progress_is_not_killed_by_the_deadline(db, make_student, make_exam):
    """A student who legitimately started ten minutes before the deadline runs past it by
    design - a 30-minute exam starting at T-10 is meant to. Their existing session must survive,
    and they must be told they are already sitting it rather than that it is closed."""
    exam = make_exam(end_time=datetime.now(timezone.utc) + timedelta(minutes=10), is_active=True)
    student = make_student(course=exam.subject.course, exam=exam)
    session = _start(student, exam, db)

    # The deadline passes while they are working.
    exam.end_time = datetime.now(timezone.utc) - timedelta(minutes=1)
    db.commit()

    with pytest.raises(HTTPException) as caught:
        _start(student, exam, db)
    assert "already has an active session" in str(caught.value.detail)

    db.refresh(session)
    assert session.status == "IN_PROGRESS"


def test_submitting_after_the_deadline_still_works(db, make_student, make_exam):
    """The deadline governs when you may begin, not whether finished work counts. Rejecting a
    late submission would destroy an attempt that was legitimate when it started."""
    exam = make_exam(end_time=datetime.now(timezone.utc) + timedelta(minutes=5), is_active=True)
    student = make_student(course=exam.subject.course, exam=exam)
    session = _start(student, exam, db)

    exam.end_time = datetime.now(timezone.utc) - timedelta(minutes=1)
    db.commit()

    submitted = ExamSessionService.submit_exam(session.id, db)

    assert submitted.status == "SUBMITTED"


def test_every_exam_has_a_deadline_for_the_gate_to_read(db, make_exam):
    """exam.end_time is NOT NULL, so there is no "deadline-less exam" hole for this gate to miss
    - which is why the check can be unconditional. start_exam still guards against None so a
    future nullable column, or a detached object, degrades to "no deadline" rather than a 500."""
    from sqlalchemy.exc import IntegrityError

    with pytest.raises(IntegrityError):
        make_exam(end_time=None, is_active=True)
    db.rollback()


def test_a_naive_deadline_does_not_500_the_student(db, make_student, make_exam):
    """Postgres' timestamptz returns tz-aware values, but a naive one reaching this comparison
    would raise TypeError and 500 a student at the exact moment they try to start. Treated as
    UTC instead."""
    exam = make_exam(is_active=True)
    student = make_student(course=exam.subject.course, exam=exam)
    exam.end_time = (datetime.now(timezone.utc) - timedelta(hours=1)).replace(tzinfo=None)

    with pytest.raises(HTTPException) as caught:
        _start(student, exam, db)

    assert caught.value.status_code == 400
