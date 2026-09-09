"""One attempt per exam, unless an instructor grants another.

Reported by the defense panel: "Student should only have limited attempts, when a student is done
with the exam, they should be no longer to be take the exam again, unless the instructor reenrolls
them for the exam."

Confirmed against the live system before fixing: a plain SUBMITTED session did not block anything.
start_exam only ever checked FLAGGED_RETAKE and RETAKE_DENIED, so the ordinary case - finish, then
immediately start again and keep the better score - fell straight through the gate.
"""
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import HTTPException

from app.models.exam_session import ExamSession
from app.services.exam_session_service import ExamSessionService


def _start(student, exam, db):
    return ExamSessionService.start_exam(student, exam.id, db)


def _finish(student, exam, db):
    session = _start(student, exam, db)
    return ExamSessionService.submit_exam(session.id, db)


def test_a_completed_exam_cannot_be_started_again(db, make_student, make_exam):
    exam = make_exam(is_active=True)
    student = make_student(course=exam.subject.course, exam=exam)
    _finish(student, exam, db)

    with pytest.raises(HTTPException) as caught:
        _start(student, exam, db)

    assert caught.value.status_code == 403
    assert "already completed" in str(caught.value.detail).lower()


def test_the_message_tells_them_who_can_unblock_it(db, make_student, make_exam):
    exam = make_exam(is_active=True)
    student = make_student(course=exam.subject.course, exam=exam)
    _finish(student, exam, db)

    with pytest.raises(HTTPException) as caught:
        _start(student, exam, db)

    # A bare "not allowed" leaves a student with nobody to ask.
    assert "instructor" in str(caught.value.detail).lower()


def test_no_second_session_row_is_created(db, make_student, make_exam):
    exam = make_exam(is_active=True)
    student = make_student(course=exam.subject.course, exam=exam)
    _finish(student, exam, db)

    with pytest.raises(HTTPException):
        _start(student, exam, db)

    assert db.query(ExamSession).filter(ExamSession.exam_id == exam.id).count() == 1


def test_an_instructor_can_re_enrol_a_student_who_simply_finished(db, make_student, make_exam):
    """The panel's "unless the instructor reenrolls them". Granting on an ordinary SUBMITTED
    attempt - a power cut, a crash, an approved absence - not only after a risk flag."""
    exam = make_exam(is_active=True)
    student = make_student(course=exam.subject.course, exam=exam)
    finished = _finish(student, exam, db)

    ExamSessionService.review_retake(finished.id, "GRANT", db)

    assert _start(student, exam, db).status == "IN_PROGRESS"


def test_a_grant_buys_exactly_one_more_attempt(db, make_student, make_exam):
    """Otherwise a single grant would reopen the exam permanently."""
    exam = make_exam(is_active=True)
    student = make_student(course=exam.subject.course, exam=exam)
    first = _finish(student, exam, db)
    ExamSessionService.review_retake(first.id, "GRANT", db)

    second = _start(student, exam, db)
    ExamSessionService.submit_exam(second.id, db)

    with pytest.raises(HTTPException) as caught:
        _start(student, exam, db)
    assert "already completed" in str(caught.value.detail).lower()


def test_a_flagged_attempt_still_awaits_review(db, make_student, make_exam):
    exam = make_exam(is_active=True)
    student = make_student(course=exam.subject.course, exam=exam)
    session = _start(student, exam, db)
    session.status = "FLAGGED_RETAKE"
    db.commit()

    with pytest.raises(HTTPException) as caught:
        _start(student, exam, db)
    assert "awaiting instructor decision" in str(caught.value.detail).lower()


def test_a_denied_retake_still_blocks(db, make_student, make_exam):
    exam = make_exam(is_active=True)
    student = make_student(course=exam.subject.course, exam=exam)
    session = _start(student, exam, db)
    session.status = "RETAKE_DENIED"
    db.commit()

    with pytest.raises(HTTPException) as caught:
        _start(student, exam, db)
    assert "denied" in str(caught.value.detail).lower()


def test_deny_still_only_applies_to_a_flagged_attempt(db, make_student, make_exam):
    """Denying a retake nobody requested is meaningless - a completed attempt is already blocked."""
    exam = make_exam(is_active=True)
    student = make_student(course=exam.subject.course, exam=exam)
    finished = _finish(student, exam, db)

    with pytest.raises(HTTPException) as caught:
        ExamSessionService.review_retake(finished.id, "DENY", db)
    assert caught.value.status_code == 400


def test_an_in_progress_attempt_cannot_be_granted_a_retake(db, make_student, make_exam):
    """They have not finished yet; granting here would hand them a second concurrent session."""
    exam = make_exam(is_active=True)
    student = make_student(course=exam.subject.course, exam=exam)
    live = _start(student, exam, db)

    with pytest.raises(HTTPException) as caught:
        ExamSessionService.review_retake(live.id, "GRANT", db)
    assert caught.value.status_code == 400


def test_another_students_attempt_does_not_block_this_one(db, make_student, make_exam):
    exam = make_exam(is_active=True)
    first = make_student(course=exam.subject.course, exam=exam)
    second = make_student(course=exam.subject.course, exam=exam)
    _finish(first, exam, db)

    assert _start(second, exam, db).status == "IN_PROGRESS"


def test_a_different_exam_is_unaffected(db, make_student, make_exam):
    exam = make_exam(is_active=True)
    other = make_exam(is_active=True, subject=exam.subject)
    student = make_student(course=exam.subject.course, exam=exam)
    db.add(__import__("app.models.exam_roster", fromlist=["ExamRoster"]).ExamRoster(
        exam_id=other.id, student_id=student.id))
    db.commit()
    _finish(student, exam, db)

    assert _start(student, other, db).status == "IN_PROGRESS"
