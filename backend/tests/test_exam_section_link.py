"""Exams reaching their term through a section.

Step 3 of the academic-hierarchy migration introduced `exams.section_id`; step 5 made it
required. School year and semester are not fields on an exam form - they are facts reached by
following one link: exam -> section -> term -> academic year.

The dual state these tests used to guard (an exam with a section and an exam without) is gone on
purpose. The "without" shape is no longer reachable, and the tests that pinned it have been
replaced by ones pinning that it is refused - see test_exam_section_required.py for the rest of
step 5.
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


def _exam_payload(section_id, **over):
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    return ExamCreate(
        title="Midterm", duration_minutes=60, total_points=10, passing_score=50,
        start_time=now, end_time=now + timedelta(hours=2),
        section_id=section_id, **over,
    )


def test_an_exam_on_a_section_reaches_its_term_and_year(
    db, default_school, make_subject, make_instructor
):
    term = _active_term(db, default_school.id)
    subject = make_subject(code="CS-101")
    instructor = make_instructor()
    section = AcademicService.create_section(
        subject.id, term.id, instructor.id, "A", default_school.id, db
    )

    exam = ExamService.create(instructor.user, _exam_payload(section.id), db)

    # The entire point: none of this is stored on the exam.
    assert exam.section_id == section.id
    assert exam.term.id == term.id
    assert exam.academic_year.label == "2026-2027"
    assert exam.term_label == "1st Semester 2026-2027"


def test_the_section_decides_the_subject_rather_than_the_request_body(
    db, default_school, make_subject, make_instructor
):
    """A body that could disagree with the section is a body that will, so it cannot carry one.

    Before step 5 subject_id was accepted and overwritten; now it is not a field at all, which is
    the difference between correcting a disagreement and making it unrepresentable.
    """
    term = _active_term(db, default_school.id)
    real, decoy = make_subject(code="CS-101"), make_subject(code="IT-999")
    instructor = make_instructor()
    section = AcademicService.create_section(
        real.id, term.id, instructor.id, "A", default_school.id, db
    )

    # Not "supplied and then overwritten" - not a field at all, which is the difference between
    # correcting a disagreement and making it unrepresentable.
    assert "subject_id" not in ExamCreate.model_fields
    assert "instructor_id" not in ExamCreate.model_fields

    exam = ExamService.create(instructor.user, _exam_payload(section.id), db)
    assert exam.subject_id == real.id
    assert exam.subject_id != decoy.id


def test_an_instructor_cannot_set_an_exam_on_someone_elses_section(
    db, default_school, make_subject, make_instructor, make_instructor_subject
):
    """The ownership check the permission layer could only ever approximate before: two
    instructors sharing a subject could each reach the other's work."""
    term = _active_term(db, default_school.id)
    subject = make_subject(code="CS-101")
    owner, intruder = make_instructor(), make_instructor()
    # Assigned to the same subject on purpose - under the old subject-assignment gate this was
    # enough to create an exam on it. Section ownership is the stronger statement.
    make_instructor_subject(owner, subject)
    make_instructor_subject(intruder, subject)
    section = AcademicService.create_section(
        subject.id, term.id, owner.id, "A", default_school.id, db
    )

    with pytest.raises(HTTPException) as caught:
        ExamService.create(intruder.user, _exam_payload(section.id), db)

    assert caught.value.status_code == 403
    assert "another instructor" in str(caught.value.detail)


def test_no_exam_can_be_added_to_a_closed_term(
    db, default_school, make_subject, make_instructor
):
    term = _active_term(db, default_school.id)
    subject = make_subject(code="CS-101")
    instructor = make_instructor()
    section = AcademicService.create_section(
        subject.id, term.id, instructor.id, "A", default_school.id, db
    )
    AcademicService.set_term_status(term.id, "CLOSED", default_school.id, db)

    with pytest.raises(HTTPException) as caught:
        ExamService.create(instructor.user, _exam_payload(section.id), db)
    assert "closed" in str(caught.value.detail).lower()


def test_a_missing_section_is_a_404_not_a_silent_null(
    db, default_school, make_subject, make_instructor
):
    make_subject()
    instructor = make_instructor()

    with pytest.raises(HTTPException) as caught:
        ExamService.create(instructor.user, _exam_payload(999999), db)
    assert caught.value.status_code == 404


def test_exams_in_one_term_can_be_found_together(
    db, default_school, make_subject, make_instructor
):
    """"Show me every exam in 1st Semester 2026-2027" - one query now, impossible before."""
    from app.models.exam import Exam
    from app.models.section import Section

    term = _active_term(db, default_school.id)
    subject = make_subject()
    instructor = make_instructor()
    section = AcademicService.create_section(
        subject.id, term.id, instructor.id, "A", default_school.id, db
    )
    ExamService.create(instructor.user, _exam_payload(section.id), db)

    # A second exam in a DIFFERENT term of the same year, which is what the filter now has to
    # exclude. Before step 5 this test used an exam with no section at all; that shape is gone.
    # The term stays PLANNED - only a CLOSED one refuses exams, and activating a second term in
    # one year is deliberately refused.
    second = AcademicService.create_term(
        term.academic_year_id, "2nd Semester", 2,
        date(2026, 11, 1), date(2027, 3, 31), default_school.id, db,
    )
    other = AcademicService.create_section(
        subject.id, second.id, instructor.id, "A", default_school.id, db
    )
    ExamService.create(instructor.user, _exam_payload(other.id), db)

    in_term = (
        db.query(Exam).join(Section, Exam.section_id == Section.id)
        .filter(Section.term_id == term.id).all()
    )

    assert len(in_term) == 1
