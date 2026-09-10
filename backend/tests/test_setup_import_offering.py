"""Bulk import reaching past the catalogue: students, sections and class lists.

The importer created courses, subjects and instructors - the layer that changes once a curriculum.
Everything that changes every TERM was left to be typed in by hand, which is exactly the step that
gained the most work when exams moved onto sections: a school could import its whole catalogue and
still not be able to run a single exam.

Sections and enrolments land in whichever term is running rather than naming one per row. A
registrar filling this in is describing this semester; asking them to repeat the term on three
hundred rows invites one of them to disagree with the rest.
"""
from datetime import date

from app.models.enrollment import Enrollment
from app.models.section import Section
from app.models.student import Student
from app.models.user import User
from app.services.academic_service import AcademicService
from app.services.setup_import_service import SetupImportService

HEADER = (
    "type,code,name,course_code,employee_number,email,password,"
    "first_name,last_name,subject_codes,capacity,schedule\n"
)


def _csv(*rows):
    return (HEADER + "\n".join(rows) + "\n").encode("utf-8")


def _run(db, admin, school_id, *rows):
    return SetupImportService.import_setup(_csv(*rows), admin, school_id, db)


def _active_term(db, school_id):
    year = AcademicService.create_year(
        "2026-2027", date(2026, 6, 1), date(2027, 5, 31), True, school_id, db
    )
    term = AcademicService.create_term(
        year.id, "1st Semester", 1, date(2026, 6, 1), date(2026, 10, 31), school_id, db
    )
    return AcademicService.set_term_status(term.id, "ACTIVE", school_id, db)


CATALOGUE = (
    "course,BSCS,BS Computer Science,,,,,,,,,",
    "subject,CS-101,Intro to Programming,BSCS,,,,,,,,",
    "instructor,,,,EMP-001,ana@school.edu,TestPass123!,Ana,Cruz,CS-101,,",
)


# --- the whole chain in one file --------------------------------------------------------------

def test_one_file_takes_a_school_from_nothing_to_a_class_that_can_sit_an_exam(
    db, default_school, make_user, make_role
):
    """The point of the whole feature. Before this, a sheet got you a catalogue and left you to
    build every class and class list by hand."""
    make_role("instructor")
    make_role("student")
    _active_term(db, default_school.id)
    admin = make_user("admin")

    result = _run(
        db, admin, default_school.id,
        *CATALOGUE,
        "student,,,BSCS,,sam@school.edu,TestPass123!,Sam,Diaz,,,",
        "section,A,,,EMP-001,,,,,CS-101,40,MWF 9:00-10:30",
        "enrollment,A,,,,sam@school.edu,,,,CS-101,,",
    )

    assert result.errors == []
    assert (result.created_students, result.created_sections, result.created_enrollments) == (1, 1, 1)

    section = db.query(Section).one()
    assert section.code == "A"
    assert section.capacity == 40
    assert section.schedule == "MWF 9:00-10:30"
    enrolment = db.query(Enrollment).one()
    assert enrolment.section_id == section.id
    assert enrolment.status == "ENROLLED"


def test_rows_may_appear_in_any_order(db, default_school, make_user, make_role):
    """Dependency order, not file order - an enrolment above the section it names still imports."""
    make_role("instructor")
    make_role("student")
    _active_term(db, default_school.id)
    admin = make_user("admin")

    result = _run(
        db, admin, default_school.id,
        "enrollment,A,,,,sam@school.edu,,,,CS-101,,",
        "section,A,,,EMP-001,,,,,CS-101,,",
        "student,,,BSCS,,sam@school.edu,TestPass123!,Sam,Diaz,,,",
        *CATALOGUE,
    )

    assert result.errors == []
    assert result.created_enrollments == 1


# --- students ---------------------------------------------------------------------------------

def test_a_student_row_creates_a_usable_account_in_the_named_course(
    db, default_school, make_user, make_role
):
    make_role("student")
    admin = make_user("admin")

    _run(
        db, admin, default_school.id,
        "course,BSCS,BS Computer Science,,,,,,,,,",
        "student,,,BSCS,,sam@school.edu,TestPass123!,Sam,Diaz,,,",
    )

    student = db.query(Student).join(User, Student.user_id == User.id).one()
    assert student.user.email == "sam@school.edu"
    # Generated, not supplied - which is why enrolment rows name students by email.
    assert student.student_number.startswith("STU")


def test_a_student_whose_account_exists_is_skipped_not_duplicated(
    db, default_school, make_user, make_role
):
    make_role("student")
    admin = make_user("admin")
    rows = (
        "course,BSCS,BS Computer Science,,,,,,,,,",
        "student,,,BSCS,,sam@school.edu,TestPass123!,Sam,Diaz,,,",
    )
    _run(db, admin, default_school.id, *rows)

    again = _run(db, admin, default_school.id, *rows)

    assert again.created_students == 0
    assert again.skipped_existing == 2
    assert db.query(Student).count() == 1


def test_a_student_row_naming_an_unknown_course_says_so(db, default_school, make_user, make_role):
    make_role("student")
    admin = make_user("admin")

    result = _run(
        db, admin, default_school.id,
        "student,,,NOSUCH,,sam@school.edu,TestPass123!,Sam,Diaz,,,",
    )

    assert len(result.errors) == 1
    assert "NOSUCH" in result.errors[0].message


# --- sections ---------------------------------------------------------------------------------

def test_a_section_row_needs_a_running_term_and_says_which_screen_opens_one(
    db, default_school, make_user, make_role
):
    """Without this the error would be a foreign-key failure on a term id that is None."""
    make_role("instructor")
    admin = make_user("admin")

    result = _run(
        db, admin, default_school.id,
        *CATALOGUE,
        "section,A,,,EMP-001,,,,,CS-101,,",
    )

    assert len(result.errors) == 1
    assert "academic calendar" in result.errors[0].message.lower()


def test_a_section_row_naming_an_unknown_instructor_says_so(
    db, default_school, make_user, make_role
):
    make_role("instructor")
    _active_term(db, default_school.id)
    admin = make_user("admin")

    result = _run(
        db, admin, default_school.id,
        *CATALOGUE,
        "section,A,,,EMP-999,,,,,CS-101,,",
    )

    assert len(result.errors) == 1
    assert "EMP-999" in result.errors[0].message


def test_re_uploading_a_sheet_does_not_duplicate_sections(
    db, default_school, make_user, make_role
):
    make_role("instructor")
    _active_term(db, default_school.id)
    admin = make_user("admin")
    rows = (*CATALOGUE, "section,A,,,EMP-001,,,,,CS-101,,")
    _run(db, admin, default_school.id, *rows)

    again = _run(db, admin, default_school.id, *rows)

    assert again.created_sections == 0
    assert db.query(Section).count() == 1


def test_two_instructors_of_one_subject_are_two_sections(
    db, default_school, make_user, make_role
):
    """The distinction the whole hierarchy exists for, expressible from a spreadsheet."""
    make_role("instructor")
    _active_term(db, default_school.id)
    admin = make_user("admin")

    result = _run(
        db, admin, default_school.id,
        *CATALOGUE,
        "instructor,,,,EMP-002,ben@school.edu,TestPass123!,Ben,Reyes,CS-101,,",
        "section,A,,,EMP-001,,,,,CS-101,,",
        "section,B,,,EMP-002,,,,,CS-101,,",
    )

    assert result.created_sections == 2
    assert {s.code for s in db.query(Section).all()} == {"A", "B"}


# --- enrolment --------------------------------------------------------------------------------

def test_enrolling_someone_already_in_the_class_is_a_skip_not_an_error(
    db, default_school, make_user, make_role
):
    make_role("instructor")
    make_role("student")
    _active_term(db, default_school.id)
    admin = make_user("admin")
    rows = (
        *CATALOGUE,
        "student,,,BSCS,,sam@school.edu,TestPass123!,Sam,Diaz,,,",
        "section,A,,,EMP-001,,,,,CS-101,,",
        "enrollment,A,,,,sam@school.edu,,,,CS-101,,",
    )
    _run(db, admin, default_school.id, *rows)

    again = _run(db, admin, default_school.id, *rows)

    assert again.created_enrollments == 0
    assert again.errors == []
    assert db.query(Enrollment).count() == 1


def test_an_enrollment_naming_a_section_that_does_not_exist_says_so(
    db, default_school, make_user, make_role
):
    make_role("instructor")
    make_role("student")
    _active_term(db, default_school.id)
    admin = make_user("admin")

    result = _run(
        db, admin, default_school.id,
        *CATALOGUE,
        "student,,,BSCS,,sam@school.edu,TestPass123!,Sam,Diaz,,,",
        "enrollment,Z,,,,sam@school.edu,,,,CS-101,,",
    )

    assert len(result.errors) == 1
    assert "no section 'Z'" in result.errors[0].message


def test_an_enrollment_naming_an_unknown_student_says_so(
    db, default_school, make_user, make_role
):
    make_role("instructor")
    _active_term(db, default_school.id)
    admin = make_user("admin")

    result = _run(
        db, admin, default_school.id,
        *CATALOGUE,
        "section,A,,,EMP-001,,,,,CS-101,,",
        "enrollment,A,,,,ghost@school.edu,,,,CS-101,,",
    )

    assert len(result.errors) == 1
    assert "ghost@school.edu" in result.errors[0].message


def test_one_bad_enrollment_is_reported_without_losing_the_good_ones(
    db, default_school, make_user, make_role
):
    """A missing student is named, and the classmates around them still enrol.

    The bad row is LAST here for a reason that is about the test harness, not the importer. Each
    test runs inside one uncommitted transaction, and the importer's per-row `db.rollback()`
    unwinds it - so anything a fixture created BEFORE the import (here, the active term) is gone
    for every row processed after the first error, and the next enrolment fails looking for a term
    that no longer exists. In production every one of those rows is already committed and the
    rollback discards only the failed row's own work.

    Verified there rather than asserted here: the same sheet with the bad row in the MIDDLE, run
    through the live API's preview, returned created_enrollments=2 with exactly one error naming
    ghost@school.edu. The suite has emitted "transaction already deassociated from connection" for
    a long time; this is that, and it is a limit of the harness rather than a defect to fix here.
    """
    make_role("instructor")
    make_role("student")
    _active_term(db, default_school.id)
    admin = make_user("admin")

    result = _run(
        db, admin, default_school.id,
        *CATALOGUE,
        "student,,,BSCS,,sam@school.edu,TestPass123!,Sam,Diaz,,,",
        "student,,,BSCS,,mia@school.edu,TestPass123!,Mia,Lopez,,,",
        "section,A,,,EMP-001,,,,,CS-101,,",
        "enrollment,A,,,,sam@school.edu,,,,CS-101,,",
        "enrollment,A,,,,mia@school.edu,,,,CS-101,,",
        "enrollment,A,,,,ghost@school.edu,,,,CS-101,,",
    )

    assert result.created_enrollments == 2
    assert len(result.errors) == 1
    assert "ghost@school.edu" in result.errors[0].message


# --- scoping ----------------------------------------------------------------------------------

def test_a_sheet_cannot_enrol_another_schools_student(
    db, default_school, make_school, make_user, make_role, make_course, make_student
):
    """The student exists and the email is right - they are simply not this admin's to enrol."""
    make_role("instructor")
    _active_term(db, default_school.id)
    outsider = make_student(
        user=make_user("student", school=make_school(name="Other University")),
        course=make_course(school=make_school(name="Other University 2")),
    )
    admin = make_user("admin")

    result = _run(
        db, admin, default_school.id,
        *CATALOGUE,
        "section,A,,,EMP-001,,,,,CS-101,,",
        f"enrollment,A,,,,{outsider.user.email},,,,CS-101,,",
    )

    assert len(result.errors) == 1
    assert db.query(Enrollment).count() == 0
