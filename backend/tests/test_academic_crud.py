"""Editing and deleting the academic hierarchy.

Until now years, terms and sections could only be created. Every other entity in the app has full
CRUD, and the gap stopped mattering quietly right up until step 5 made a section mandatory on an
exam: a section built with the wrong instructor could not be corrected, and since exams derive
their instructor from the section, every exam on it was attributed to the wrong person with no
route back except editing the database by hand.

Two rules are being pinned:

  1. **Delete refuses while anything depends on it, and says what.** Not a cascade - a school year
     cascade would take terms, sections, class lists and exams, which is not what anybody means
     by "delete this year".
  2. **Reassigning a section takes its exams with it.** That is the whole point of exams deriving
     instructor_id from the section; leaving them behind would reintroduce the drift step 5
     removed.
"""
from datetime import date

import pytest
from fastapi import HTTPException

from app.models.exam import Exam
from app.services.academic_service import AcademicService


def _year(db, school_id, label="2026-2027"):
    return AcademicService.create_year(
        label, date(2026, 6, 1), date(2027, 5, 31), True, school_id, db
    )


def _term(db, school_id, year, name="1st Semester", sequence=1):
    return AcademicService.create_term(
        year.id, name, sequence, date(2026, 6, 1), date(2026, 10, 31), school_id, db
    )


# --- years ------------------------------------------------------------------------------------

def test_a_year_can_be_renamed_and_redated(db, default_school):
    year = _year(db, default_school.id)

    updated = AcademicService.update_year(
        year.id, default_school.id, db, "AY 2026-27", date(2026, 8, 1), date(2027, 6, 30)
    )

    assert updated.label == "AY 2026-27"
    assert updated.starts_on == date(2026, 8, 1)


def test_renaming_a_year_onto_another_years_label_is_refused(db, default_school):
    _year(db, default_school.id, "2026-2027")
    second = _year(db, default_school.id, "2027-2028")

    with pytest.raises(HTTPException) as caught:
        AcademicService.update_year(
            second.id, default_school.id, db, "2026-2027", date(2027, 6, 1), date(2028, 5, 31)
        )

    assert "already exists" in str(caught.value.detail)


def test_a_year_may_keep_its_own_label_while_its_dates_change(db, default_school):
    """The uniqueness check has to exclude the row being edited, or no year could ever be redated
    without also being renamed."""
    year = _year(db, default_school.id)

    updated = AcademicService.update_year(
        year.id, default_school.id, db, "2026-2027", date(2026, 7, 1), date(2027, 5, 31)
    )

    assert updated.starts_on == date(2026, 7, 1)


def test_a_year_with_terms_is_not_deleted(db, default_school):
    year = _year(db, default_school.id)
    _term(db, default_school.id, year)

    with pytest.raises(HTTPException) as caught:
        AcademicService.delete_year(year.id, default_school.id, db)

    assert caught.value.status_code == 400
    assert "1 term" in str(caught.value.detail)


def test_an_empty_year_is_deleted(db, default_school):
    year = _year(db, default_school.id)

    AcademicService.delete_year(year.id, default_school.id, db)

    assert AcademicService.list_years(default_school.id, db) == []


# --- terms ------------------------------------------------------------------------------------

def test_a_term_can_be_renamed_and_repositioned(db, default_school):
    year = _year(db, default_school.id)
    term = _term(db, default_school.id, year)

    updated = AcademicService.update_term(
        term.id, default_school.id, db, "First Semester", 2,
        date(2026, 6, 15), date(2026, 11, 15),
    )

    assert (updated.name, updated.sequence) == ("First Semester", 2)


def test_two_terms_cannot_share_a_position(db, default_school):
    year = _year(db, default_school.id)
    _term(db, default_school.id, year, "1st Semester", 1)
    second = _term(db, default_school.id, year, "2nd Semester", 2)

    with pytest.raises(HTTPException) as caught:
        AcademicService.update_term(
            second.id, default_school.id, db, "2nd Semester", 1,
            date(2026, 11, 1), date(2027, 3, 31),
        )

    assert "position 1" in str(caught.value.detail)


def test_editing_a_term_cannot_change_its_status(db, default_school):
    """Status is a state machine with side effects - closing completes every enrolment in the
    term - so it is not something a rename form can carry."""
    from app.schemas.academic import TermUpdate

    assert "status" not in TermUpdate.model_fields
    assert "academic_year_id" not in TermUpdate.model_fields


def test_a_term_with_sections_is_not_deleted(db, default_school, make_subject, make_instructor):
    year = _year(db, default_school.id)
    term = _term(db, default_school.id, year)
    AcademicService.create_section(
        make_subject().id, term.id, make_instructor().id, "A", default_school.id, db
    )

    with pytest.raises(HTTPException) as caught:
        AcademicService.delete_term(term.id, default_school.id, db)

    assert "1 section" in str(caught.value.detail)


# --- sections ---------------------------------------------------------------------------------

def test_a_sections_code_and_details_can_be_corrected(db, default_school, make_subject, make_instructor):
    year = _year(db, default_school.id)
    term = _term(db, default_school.id, year)
    instructor = make_instructor()
    section = AcademicService.create_section(
        make_subject().id, term.id, instructor.id, "A", default_school.id, db
    )

    updated = AcademicService.update_section(
        section.id, default_school.id, db, "BSCS-3A", instructor.id,
        capacity=45, schedule="MWF 9:00-10:30",
    )

    assert (updated.code, updated.capacity, updated.schedule) == ("BSCS-3A", 45, "MWF 9:00-10:30")


def test_reassigning_a_section_moves_its_exams_to_the_new_instructor(
    db, default_school, make_subject, make_instructor, make_exam
):
    """The reason exams derive instructor_id from the section instead of storing their own copy.

    Leaving the exams behind would put them under an instructor who no longer teaches the class -
    exactly the drift step 5 exists to prevent, reintroduced by the edit form.
    """
    year = _year(db, default_school.id)
    term = _term(db, default_school.id, year)
    subject = make_subject()
    original, replacement = make_instructor(), make_instructor()
    section = AcademicService.create_section(
        subject.id, term.id, original.id, "A", default_school.id, db
    )
    exam = make_exam(subject=subject, instructor=original, section=section)

    AcademicService.update_section(
        section.id, default_school.id, db, "A", replacement.id
    )

    db.refresh(exam)
    assert exam.instructor_id == replacement.id


def test_a_section_cannot_be_handed_to_another_schools_instructor(
    db, default_school, make_subject, make_instructor, make_user, make_school
):
    year = _year(db, default_school.id)
    term = _term(db, default_school.id, year)
    section = AcademicService.create_section(
        make_subject().id, term.id, make_instructor().id, "A", default_school.id, db
    )
    outsider = make_instructor(user=make_user("instructor", school=make_school(name="Other U")))

    with pytest.raises(HTTPException) as caught:
        AcademicService.update_section(section.id, default_school.id, db, "A", outsider.id)

    assert caught.value.status_code == 404


def test_two_sections_of_one_subject_cannot_share_a_code_in_one_term(
    db, default_school, make_subject, make_instructor
):
    year = _year(db, default_school.id)
    term = _term(db, default_school.id, year)
    subject = make_subject()
    instructor = make_instructor()
    AcademicService.create_section(subject.id, term.id, instructor.id, "A", default_school.id, db)
    second = AcademicService.create_section(
        subject.id, term.id, instructor.id, "B", default_school.id, db
    )

    with pytest.raises(HTTPException) as caught:
        AcademicService.update_section(second.id, default_school.id, db, "A", instructor.id)

    assert "already exists" in str(caught.value.detail)


def test_a_section_with_an_exam_is_not_deleted(
    db, default_school, make_subject, make_instructor, make_exam
):
    """Without this the database refuses it anyway - exams.section_id is NOT NULL - but with a
    foreign-key error naming a constraint instead of a sentence about exams."""
    year = _year(db, default_school.id)
    term = _term(db, default_school.id, year)
    subject = make_subject()
    instructor = make_instructor()
    section = AcademicService.create_section(
        subject.id, term.id, instructor.id, "A", default_school.id, db
    )
    make_exam(subject=subject, instructor=instructor, section=section)

    with pytest.raises(HTTPException) as caught:
        AcademicService.delete_section(section.id, default_school.id, db)

    assert "1 exam is set on this section" in str(caught.value.detail)


def test_a_section_with_a_class_list_is_not_deleted(
    db, default_school, make_subject, make_instructor, make_student
):
    """A class list is work somebody did. Cascading it away on a mis-click is not recoverable
    from the UI, so it is refused rather than silently taken."""
    year = _year(db, default_school.id)
    term = _term(db, default_school.id, year)
    section = AcademicService.create_section(
        make_subject().id, term.id, make_instructor().id, "A", default_school.id, db
    )
    AcademicService.enroll(section.id, [make_student().id], default_school.id, db)

    with pytest.raises(HTTPException) as caught:
        AcademicService.delete_section(section.id, default_school.id, db)

    assert "1 student is enrolled" in str(caught.value.detail)


def test_an_unused_section_is_deleted(db, default_school, make_subject, make_instructor):
    year = _year(db, default_school.id)
    term = _term(db, default_school.id, year)
    section = AcademicService.create_section(
        make_subject().id, term.id, make_instructor().id, "A", default_school.id, db
    )

    AcademicService.delete_section(section.id, default_school.id, db)

    assert AcademicService.list_sections(default_school.id, db) == []


# --- permissions ------------------------------------------------------------------------------

def test_an_instructor_cannot_edit_or_delete_the_hierarchy(
    client, db, default_school, make_subject, make_instructor, auth_headers
):
    """Creation is require_admin; the new verbs have to match, or the gap becomes the way in."""
    year = _year(db, default_school.id)
    term = _term(db, default_school.id, year)
    instructor = make_instructor()
    section = AcademicService.create_section(
        make_subject().id, term.id, instructor.id, "A", default_school.id, db
    )
    headers = auth_headers(instructor.user)

    assert client.delete(f"/academic/years/{year.id}", headers=headers).status_code == 403
    assert client.delete(f"/academic/terms/{term.id}", headers=headers).status_code == 403
    assert client.delete(f"/academic/sections/{section.id}", headers=headers).status_code == 403
    assert client.put(
        f"/academic/sections/{section.id}",
        headers=headers,
        json={"code": "X", "instructor_id": instructor.id},
    ).status_code == 403


def test_an_admin_cannot_reach_another_schools_year(
    client, db, default_school, make_school, make_user, auth_headers
):
    other = make_school(name="Other University")
    foreign_year = _year(db, other.id)
    admin = make_user("admin")

    response = client.delete(f"/academic/years/{foreign_year.id}", headers=auth_headers(admin))

    assert response.status_code == 404
