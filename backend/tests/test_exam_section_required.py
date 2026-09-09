"""A section is required on an exam, and it is the only statement of subject and instructor.

Step 5 of the academic-hierarchy migration. Steps 3 and 4 left `exams.section_id` nullable so old
and new shapes could coexist; this is where that dual state ends.

Two things are being pinned here, and the second is the one with teeth:

  1. An exam cannot exist without a section (schema and API).
  2. subject_id and instructor_id are DERIVED from that section on every write. They are not
     fields a client can send, so a request body can no longer disagree with the class an exam
     belongs to - not "disagree and get corrected", but disagree at all.
"""
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import HTTPException

from app.schemas.exam import ExamCreate, ExamUpdate
from app.services.academic_service import AcademicService
from app.services.exam_service import ExamService


def _payload(section_id, **over):
    now = datetime.now(timezone.utc)
    return {
        "title": "Midterm",
        "duration_minutes": 30,
        "passing_score": 50,
        "start_time": now.isoformat(),
        "end_time": (now + timedelta(hours=1)).isoformat(),
        "section_id": section_id,
        **over,
    }


# --- required ---------------------------------------------------------------------------------

def test_creating_an_exam_without_a_section_is_refused(client, make_section, auth_headers):
    section = make_section()
    body = _payload(section.id)
    del body["section_id"]

    response = client.post("/exams/", headers=auth_headers(section.instructor.user), json=body)

    assert response.status_code == 422
    assert "section_id" in response.text


def test_the_schema_does_not_accept_a_subject_or_instructor_at_all():
    """Not "accepted and overwritten" - absent. A field that cannot be sent cannot be wrong."""
    assert "subject_id" not in ExamCreate.model_fields
    assert "instructor_id" not in ExamCreate.model_fields
    assert "subject_id" not in ExamUpdate.model_fields
    assert "instructor_id" not in ExamUpdate.model_fields


# --- derived ----------------------------------------------------------------------------------

def test_an_admin_creating_an_exam_attributes_it_to_whoever_teaches_the_section(
    client, make_section, make_user, auth_headers
):
    """The admin path used to name an instructor in the body, which is a second copy of a fact the
    section already holds - and one an admin could get wrong, or a compromised admin abuse."""
    section = make_section()
    admin = make_user("admin")

    response = client.post("/exams/", headers=auth_headers(admin), json=_payload(section.id))

    assert response.status_code == 200, response.text
    assert response.json()["instructor_id"] == section.instructor_id
    assert response.json()["subject_id"] == section.subject_id


def test_an_admin_cannot_reach_another_schools_section(
    client, make_section, make_subject, make_course, make_school, make_user, auth_headers
):
    """Scoping for the admin path, which has no instructor record to check ownership against."""
    other_school = make_school(name="Other University")
    foreign = make_section(subject=make_subject(course=make_course(school=other_school)))
    admin = make_user("admin")

    response = client.post("/exams/", headers=auth_headers(admin), json=_payload(foreign.id))

    assert response.status_code == 404


# --- moving an exam ---------------------------------------------------------------------------

def test_moving_an_exam_to_another_section_re_derives_its_subject_and_instructor(
    db, default_school, make_instructor, make_subject, make_section, make_exam, make_term
):
    """A move changes what class the exam belongs to, so the facts that come from the class have
    to move with it - otherwise the exam keeps filing itself under the subject it left."""
    instructor = make_instructor()
    exam = make_exam(instructor=instructor)
    elsewhere = make_section(subject=make_subject(code="IT-200"), instructor=instructor)

    updated = ExamService.update(
        exam.id, instructor.user, ExamUpdate(section_id=elsewhere.id), db
    )

    assert updated.section_id == elsewhere.id
    assert updated.subject_id == elsewhere.subject_id


def test_an_instructor_cannot_move_their_exam_onto_someone_elses_section(
    db, default_school, make_instructor, make_section, make_exam
):
    """The check that owning the exam does not cover.

    require_exam_owner proves the caller may change THIS exam; it says nothing about where they
    may move it to. Without a check on the TARGET, an instructor could file their own exam under a
    colleague's class - and, since instructor_id follows the section, hand it to them outright.
    """
    mine = make_instructor()
    exam = make_exam(instructor=mine)
    theirs = make_section()

    with pytest.raises(HTTPException) as caught:
        ExamService.update(exam.id, mine.user, ExamUpdate(section_id=theirs.id), db)

    assert caught.value.status_code == 403
    assert "another instructor" in str(caught.value.detail)


def test_an_exam_cannot_be_moved_into_a_closed_term(
    db, default_school, make_instructor, make_subject, make_exam, make_section, make_term
):
    """Closing a term completes its class lists; letting an exam move in afterwards would put a
    sitting into a term that has already been finalised."""
    from datetime import date

    instructor = make_instructor()
    exam = make_exam(instructor=instructor)

    year = AcademicService.create_year(
        "2027-2028", date(2027, 6, 1), date(2028, 5, 31), False, default_school.id, db
    )
    old_term = AcademicService.create_term(
        year.id, "Past Semester", 1, date(2027, 6, 1), date(2027, 10, 31), default_school.id, db
    )
    AcademicService.set_term_status(old_term.id, "ACTIVE", default_school.id, db)
    target = AcademicService.create_section(
        make_subject(code="HIST-1").id, old_term.id, instructor.id, "A", default_school.id, db
    )
    AcademicService.set_term_status(old_term.id, "CLOSED", default_school.id, db)

    with pytest.raises(HTTPException) as caught:
        ExamService.update(exam.id, instructor.user, ExamUpdate(section_id=target.id), db)

    assert "closed" in str(caught.value.detail).lower()


def test_an_update_that_does_not_mention_the_section_leaves_it_alone(
    db, default_school, make_instructor, make_exam
):
    """Renaming an exam must not disturb what it belongs to - exclude_unset, not a defaulted None
    that would read as "move this exam to nowhere"."""
    instructor = make_instructor()
    exam = make_exam(instructor=instructor)
    original_section = exam.section_id

    updated = ExamService.update(exam.id, instructor.user, ExamUpdate(title="Renamed"), db)

    assert updated.title == "Renamed"
    assert updated.section_id == original_section
