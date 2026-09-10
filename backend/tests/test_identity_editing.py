"""Correcting a person's name or sign-in address.

Reported in QA: the instructor edit form changed the employee number and nothing else. The reason
was structural rather than an oversight in the form - name and email live on the linked User row,
and both `InstructorUpdate` and `StudentUpdate` could only reach the profile row. So the single
most likely reason to open an edit form, a misspelled name or a wrong address, was the one thing
it could not do.

Both entities go through one shared helper, because renaming an instructor and renaming a student
are the same act on two different profile types.
"""
import pytest
from fastapi import HTTPException

from app.schemas.instructor import InstructorUpdate
from app.schemas.student import StudentUpdate
from app.services.instructor_service import InstructorService
from app.services.student_service import StudentService


# --- instructors -------------------------------------------------------------------------------

def test_an_instructors_name_can_be_corrected(db, make_instructor, make_user):
    instructor = make_instructor()
    admin = make_user("admin")

    updated = InstructorService.update(
        instructor.id, InstructorUpdate(first_name="Anna", last_name="Cruz-Reyes"), admin, db
    )

    assert updated.user.first_name == "Anna"
    assert updated.instructor_name == "Anna Cruz-Reyes"


def test_an_instructors_email_can_be_corrected(db, make_instructor, make_user):
    instructor = make_instructor()
    admin = make_user("admin")

    updated = InstructorService.update(
        instructor.id, InstructorUpdate(email="new.address@school.edu"), admin, db
    )

    assert updated.user.email == "new.address@school.edu"


def test_editing_only_the_employee_number_leaves_the_person_alone(db, make_instructor, make_user):
    """exclude_unset semantics by another name: a form that submits one field must not blank the
    others out."""
    instructor = make_instructor()
    original_name = instructor.user.first_name
    original_email = instructor.user.email
    admin = make_user("admin")

    InstructorService.update(instructor.id, InstructorUpdate(employee_number="EMP-999"), admin, db)

    assert instructor.employee_number == "EMP-999"
    assert instructor.user.first_name == original_name
    assert instructor.user.email == original_email


def test_an_email_already_in_use_is_refused_rather_than_500ing(
    db, make_instructor, make_user
):
    """Without the check this surfaces as an IntegrityError on the unique index - a 500 with no
    indication of which field was the problem."""
    taken = make_instructor()
    other = make_instructor()
    admin = make_user("admin")

    with pytest.raises(HTTPException) as caught:
        InstructorService.update(
            other.id, InstructorUpdate(email=taken.user.email), admin, db
        )

    assert caught.value.status_code == 400
    assert "already exists" in str(caught.value.detail).lower()


def test_an_email_differing_only_in_case_is_still_a_duplicate(db, make_instructor, make_user):
    """The bug this repeats a guard for: a case-sensitive check let "Name@x.com" through beside
    "name@x.com", and login - which compares case-insensitively - could then reach only one."""
    taken = make_instructor()
    other = make_instructor()
    admin = make_user("admin")

    with pytest.raises(HTTPException):
        InstructorService.update(
            other.id, InstructorUpdate(email=taken.user.email.upper()), admin, db
        )


def test_an_email_is_stored_normalised(db, make_instructor, make_user):
    instructor = make_instructor()
    admin = make_user("admin")

    updated = InstructorService.update(
        instructor.id, InstructorUpdate(email="  MiXeD.Case@School.Edu  "), admin, db
    )

    assert updated.user.email == "mixed.case@school.edu"


def test_keeping_your_own_email_is_not_a_duplicate(db, make_instructor, make_user):
    """Re-submitting an unchanged form must not fail on the row it is editing."""
    instructor = make_instructor()
    admin = make_user("admin")

    updated = InstructorService.update(
        instructor.id,
        InstructorUpdate(email=instructor.user.email, first_name="Renamed"),
        admin,
        db,
    )

    assert updated.user.first_name == "Renamed"


def test_changing_to_a_mistyped_provider_is_caught(db, make_instructor, make_user):
    """An edit is exactly where somebody retypes an address by hand, and gmail.cmo can never
    receive a password reset."""
    instructor = make_instructor()
    admin = make_user("admin")

    with pytest.raises(HTTPException) as caught:
        InstructorService.update(
            instructor.id, InstructorUpdate(email="jrizal@gmail.cmo"), admin, db
        )

    assert "gmail.com" in str(caught.value.detail)


def test_a_record_that_already_has_a_mistyped_address_can_still_be_edited(
    db, make_instructor, make_user
):
    """The trap this avoids, and it is live data: jrizal@gmail.cmo is a real row.

    Guarding on the schema instead would validate every submission, including the unchanged
    address the edit form resubmits - making the one account that HAS the typo the one account
    nobody can edit at all, not even to correct the owner's name. The guard therefore fires on a
    CHANGE, which is the only moment a new typo can be introduced.
    """
    instructor = make_instructor()
    instructor.user.email = "jrizal@gmail.cmo"
    db.commit()
    admin = make_user("admin")

    updated = InstructorService.update(
        instructor.id,
        InstructorUpdate(first_name="Jose Protacio", email="jrizal@gmail.cmo"),
        admin,
        db,
    )

    assert updated.user.first_name == "Jose Protacio"
    assert updated.user.email == "jrizal@gmail.cmo"


def test_correcting_a_mistyped_address_is_allowed(db, make_instructor, make_user):
    """And the way out: changing it to the real domain passes the guard."""
    instructor = make_instructor()
    instructor.user.email = "jrizal@gmail.cmo"
    db.commit()
    admin = make_user("admin")

    updated = InstructorService.update(
        instructor.id, InstructorUpdate(email="jrizal@gmail.com"), admin, db
    )

    assert updated.user.email == "jrizal@gmail.com"


# --- students ----------------------------------------------------------------------------------

def test_a_students_name_and_email_can_be_corrected(db, make_student, make_user):
    student = make_student()
    admin = make_user("admin")

    updated = StudentService.update(
        student.id,
        StudentUpdate(first_name="Maria", last_name="Santos", email="maria.santos@school.edu"),
        admin,
        db,
    )

    assert updated.student_name == "Maria Santos"
    assert updated.user.email == "maria.santos@school.edu"


def test_editing_a_students_accommodations_leaves_their_name_alone(db, make_student, make_user):
    student = make_student()
    original = student.user.first_name
    admin = make_user("admin")

    StudentService.update(student.id, StudentUpdate(extra_time_minutes=30), admin, db)

    assert student.extra_time_minutes == 30
    assert student.user.first_name == original


def test_a_students_email_cannot_collide_with_an_instructors(db, make_student, make_instructor, make_user):
    """One users table - the duplicate check has to span every role, not just the one being
    edited."""
    student = make_student()
    instructor = make_instructor()
    admin = make_user("admin")

    with pytest.raises(HTTPException) as caught:
        StudentService.update(
            student.id, StudentUpdate(email=instructor.user.email), admin, db
        )

    assert caught.value.status_code == 400
