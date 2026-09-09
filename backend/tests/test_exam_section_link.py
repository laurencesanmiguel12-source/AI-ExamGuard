"""Exams reaching their term through a section.

Step 3 of the academic-hierarchy migration. `exams.section_id` is nullable and subject_id /
instructor_id are still in place, so both the old and new shapes have to keep working - that dual
state is the whole point of doing this in steps, and it is what these tests guard.

The payoff: school year and semester stop being fields on an exam form and become facts reached
by following one link.
"""
from datetime import date, timedelta

import pytest
from fastapi import HTTPException

from app.schemas.exam import ExamCreate
from app.services.academic_service import AcademicService
from app.services.exam_service import ExamService


def _active_term(db, school_id):
    year = AcademicService.create_year(
        "2026-2027", date(2026, 6, 1), date(2027, 5, 31), True, school_id, db
    )
    term = AcademicService.create_term(
        year.id, "1st Semester", 1, date(2026, 6, 1), date(2026, 10, 31), school_id, db
    )
    return AcademicService.set_term_status(term.id, "ACTIVE", school_id, db)


def _exam_payload(subject_id, instructor_id, **over):
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    return ExamCreate(
        title="Midterm", duration_minutes=60, total_points=10, passing_score=50,
        start_time=now, end_time=now + timedelta(hours=2),
        subject_id=subject_id, instructor_id=instructor_id, **over,
    )


def test_an_exam_on_a_section_reaches_its_term_and_year(
    db, default_school, make_subject, make_instructor, make_instructor_subject
):
    term = _active_term(db, default_school.id)
    subject = make_subject(code="CS-101")
    instructor = make_instructor()
    make_instructor_subject(instructor, subject)
    section = AcademicService.create_section(
        subject.id, term.id, instructor.id, "A", default_school.id, db
    )

    exam = ExamService.create(
        instructor, _exam_payload(subject.id, instructor.id, section_id=section.id), db
    )

    # The entire point: none of this is stored on the exam.
    assert exam.section_id == section.id
    assert exam.term.id == term.id
    assert exam.academic_year.label == "2026-2027"
    assert exam.term_label == "1st Semester 2026-2027"


def test_the_section_decides_the_subject_rather_than_the_request_body(
    db, default_school, make_subject, make_instructor, make_instructor_subject
):
    """Otherwise an exam could claim a section of CS-101 while filing itself under another
    subject, and the two would drift apart with nothing to catch it."""
    term = _active_term(db, default_school.id)
    real, decoy = make_subject(code="CS-101"), make_subject(code="IT-999")
    instructor = make_instructor()
    make_instructor_subject(instructor, real)
    make_instructor_subject(instructor, decoy)
    section = AcademicService.create_section(
        real.id, term.id, instructor.id, "A", default_school.id, db
    )

    exam = ExamService.create(
        instructor, _exam_payload(decoy.id, instructor.id, section_id=section.id), db
    )

    assert exam.subject_id == real.id


def test_an_instructor_cannot_set_an_exam_on_someone_elses_section(
    db, default_school, make_subject, make_instructor, make_instructor_subject
):
    """The ownership check the permission layer could only ever approximate before: two
    instructors sharing a subject could each reach the other's work."""
    term = _active_term(db, default_school.id)
    subject = make_subject(code="CS-101")
    owner, intruder = make_instructor(), make_instructor()
    make_instructor_subject(owner, subject)
    make_instructor_subject(intruder, subject)
    section = AcademicService.create_section(
        subject.id, term.id, owner.id, "A", default_school.id, db
    )

    with pytest.raises(HTTPException) as caught:
        ExamService.create(
            intruder, _exam_payload(subject.id, intruder.id, section_id=section.id), db
        )

    assert caught.value.status_code == 403
    assert "another instructor" in str(caught.value.detail)


def test_no_exam_can_be_added_to_a_closed_term(
    db, default_school, make_subject, make_instructor, make_instructor_subject
):
    term = _active_term(db, default_school.id)
    subject = make_subject(code="CS-101")
    instructor = make_instructor()
    make_instructor_subject(instructor, subject)
    section = AcademicService.create_section(
        subject.id, term.id, instructor.id, "A", default_school.id, db
    )
    AcademicService.set_term_status(term.id, "CLOSED", default_school.id, db)

    with pytest.raises(HTTPException) as caught:
        ExamService.create(
            instructor, _exam_payload(subject.id, instructor.id, section_id=section.id), db
        )
    assert "closed" in str(caught.value.detail).lower()


def test_a_missing_section_is_a_404_not_a_silent_null(
    db, default_school, make_subject, make_instructor, make_instructor_subject
):
    subject = make_subject()
    instructor = make_instructor()
    make_instructor_subject(instructor, subject)

    with pytest.raises(HTTPException) as caught:
        ExamService.create(
            instructor, _exam_payload(subject.id, instructor.id, section_id=999999), db
        )
    assert caught.value.status_code == 404


# --- the old shape must keep working through the migration ------------------------------------

def test_an_exam_without_a_section_still_works(
    db, default_school, make_subject, make_instructor, make_instructor_subject
):
    """section_id is nullable on purpose in step 3. Existing code paths that never heard of
    sections must not start failing."""
    subject = make_subject()
    instructor = make_instructor()
    make_instructor_subject(instructor, subject)

    exam = ExamService.create(instructor, _exam_payload(subject.id, instructor.id), db)

    assert exam.section_id is None
    assert exam.subject_id == subject.id


def test_term_accessors_degrade_to_none_rather_than_raising(
    db, default_school, make_subject, make_instructor, make_instructor_subject
):
    """Anything rendering an exam list would otherwise crash on the first un-migrated row."""
    subject = make_subject()
    instructor = make_instructor()
    make_instructor_subject(instructor, subject)
    exam = ExamService.create(instructor, _exam_payload(subject.id, instructor.id), db)

    assert exam.term is None
    assert exam.academic_year is None
    assert exam.term_label is None


def test_exams_in_one_term_can_be_found_together(
    db, default_school, make_subject, make_instructor, make_instructor_subject
):
    """"Show me every exam in 1st Semester 2026-2027" - one query now, impossible before."""
    from app.models.exam import Exam
    from app.models.section import Section

    term = _active_term(db, default_school.id)
    subject = make_subject()
    instructor = make_instructor()
    make_instructor_subject(instructor, subject)
    section = AcademicService.create_section(
        subject.id, term.id, instructor.id, "A", default_school.id, db
    )
    ExamService.create(
        instructor, _exam_payload(subject.id, instructor.id, section_id=section.id), db
    )
    ExamService.create(instructor, _exam_payload(subject.id, instructor.id), db)  # no section

    in_term = (
        db.query(Exam).join(Section, Exam.section_id == Section.id)
        .filter(Section.term_id == term.id).all()
    )

    assert len(in_term) == 1
