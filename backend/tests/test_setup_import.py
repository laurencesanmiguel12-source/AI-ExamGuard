"""Bulk setup import: one CSV creating courses, subjects and instructors.

The behaviours worth pinning down are the ones that make it usable on a real registrar's
spreadsheet: rows referencing each other by code, dependency order regardless of row order, one
bad row not taking the file down with it, and re-uploading an edited sheet being safe.
"""
import io

from app.models.course import Course
from app.models.instructor import Instructor
from app.models.instructor_subject import InstructorSubject
from app.models.subject import Subject
from app.models.user import User
from app.services.setup_import_service import SetupImportService

HEADER = ("type,code,name,course_code,employee_number,email,password,"
          "first_name,last_name,subject_codes\n")


def _csv(*lines):
    return (HEADER + "".join(line + "\n" for line in lines)).encode("utf-8")


def _run(db, admin, body):
    return SetupImportService.import_setup(body, admin, admin.school_id, db)


def test_imports_a_whole_academic_structure_from_one_file(db, make_user, make_role):
    make_role("instructor")
    admin = make_user("admin")

    result = _run(db, admin, _csv(
        "course,BSCS,BS Computer Science,,,,,,,",
        "subject,CS-101,Programming 1,BSCS,,,,,,",
        "instructor,,,,EMP-001,ana@school.edu,TestPass123!,Ana,Cruz,CS-101",
    ))

    assert (result.created_courses, result.created_subjects, result.created_instructors) == (1, 1, 1)
    assert result.errors == []

    course = db.query(Course).filter(Course.code == "BSCS").one()
    subject = db.query(Subject).filter(Subject.code == "CS-101").one()
    assert subject.course_id == course.id
    # The instructor is usable immediately - assigned to the subject, so they can set an exam.
    instructor = db.query(Instructor).filter(Instructor.employee_number == "EMP-001").one()
    assert db.query(InstructorSubject).filter(
        InstructorSubject.instructor_id == instructor.id,
        InstructorSubject.subject_id == subject.id,
    ).count() == 1


def test_row_order_does_not_matter(db, make_user, make_role):
    """A registrar's sheet is grouped however they grouped it. Processing follows dependency
    order, not file order, so a subject listed above its course still imports."""
    make_role("instructor")
    admin = make_user("admin")

    result = _run(db, admin, _csv(
        "instructor,,,,EMP-002,bo@school.edu,TestPass123!,Bo,Reyes,IT-201",
        "subject,IT-201,Networking,BSIT,,,,,,",
        "course,BSIT,BS Information Technology,,,,,,,",
    ))

    assert (result.created_courses, result.created_subjects, result.created_instructors) == (1, 1, 1)
    assert result.errors == []


def test_re_uploading_an_edited_sheet_adds_only_what_is_new(db, make_user, make_role):
    """Adding a few rows and re-uploading is normal. It should not produce a wall of duplicate
    errors."""
    make_role("instructor")
    admin = make_user("admin")
    first = _csv("course,BSCS,BS Computer Science,,,,,,,")
    _run(db, admin, first)

    result = _run(db, admin, _csv(
        "course,BSCS,BS Computer Science,,,,,,,",
        "course,BSIT,BS Information Technology,,,,,,,",
    ))

    assert result.created_courses == 1
    assert result.skipped_existing == 1
    assert result.errors == []


def test_one_bad_row_does_not_abandon_the_rest(db, make_user, make_role):
    make_role("instructor")
    admin = make_user("admin")

    result = _run(db, admin, _csv(
        "course,BSCS,BS Computer Science,,,,,,,",
        "subject,CS-101,Programming 1,NOSUCHCOURSE,,,,,,",
        "course,BSIT,BS Information Technology,,,,,,,",
    ))

    assert result.created_courses == 2
    assert len(result.errors) == 1
    assert result.errors[0].row == 3          # the line number in their spreadsheet
    assert "NOSUCHCOURSE" in result.errors[0].message


def test_names_the_missing_field_rather_than_failing_vaguely(db, make_user, make_role):
    make_role("instructor")
    admin = make_user("admin")

    result = _run(db, admin, _csv("course,BSCS,,,,,,,,"))

    assert result.created_courses == 0
    assert "code and name" in result.errors[0].message


def test_rejects_a_file_without_a_type_column(db, make_user):
    admin = make_user("admin")

    try:
        SetupImportService.import_setup(b"code,name\nBSCS,Computer Science\n",
                                        admin, admin.school_id, db)
        assert False, "should have refused a file with no type column"
    except Exception as e:
        assert "type" in str(e.detail if hasattr(e, "detail") else e)


def test_an_unknown_type_is_reported_against_its_row(db, make_user):
    admin = make_user("admin")

    result = _run(db, admin, _csv("teacher,,,,EMP-9,x@y.edu,TestPass123!,X,Y,"))

    assert result.errors[0].row == 2
    assert "type must be one of" in result.errors[0].message


def test_import_cannot_write_into_another_school(db, make_user, make_role, make_school):
    """school_id comes from the session, never the file."""
    make_role("instructor")
    other_school = make_school()
    admin = make_user("admin")

    _run(db, admin, _csv("course,BSCS,BS Computer Science,,,,,,,"))

    course = db.query(Course).filter(Course.code == "BSCS").one()
    assert course.school_id == admin.school_id
    assert course.school_id != other_school.id


def test_an_instructor_row_without_a_password_is_refused(db, make_user, make_role):
    """The account is created ready to sign in, so a blank password would either fail deep in the
    auth layer or create something unusable."""
    make_role("instructor")
    admin = make_user("admin")

    result = _run(db, admin, _csv(
        "instructor,,,,EMP-003,cy@school.edu,,Cy,Santos,",
    ))

    assert result.created_instructors == 0
    assert "password" in result.errors[0].message


def test_blank_spacer_rows_are_ignored(db, make_user, make_role):
    """People group sections with an empty line. That is formatting, not an error."""
    make_role("instructor")
    admin = make_user("admin")

    result = _run(db, admin, _csv(
        "course,BSCS,BS Computer Science,,,,,,,",
        ",,,,,,,,,",
        "course,BSIT,BS Information Technology,,,,,,,",
    ))

    assert result.created_courses == 2
    assert result.errors == []
