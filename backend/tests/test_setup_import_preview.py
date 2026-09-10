"""The bulk-import dry run.

The defense panel asked to see duplicates and bad formatting *before* anything is written. The
tempting way to answer that is a second pass that re-checks the rows - which is exactly the "two
definitions of correct" the import service's own docstring warns against. A preview that validates
differently from the importer is worse than no preview, because it is trusted.

So the preview runs the importer itself against a throwaway session and rolls it back. These tests
pin the two things that makes it worth having: it reports exactly what a real import would report,
and it writes nothing at all.
"""
from app.models.course import Course
from app.models.instructor import Instructor
from app.models.subject import Subject
from app.models.user import User

CSV = (
    "type,code,name,course_code,employee_number,email,password,first_name,last_name,subject_codes\n"
    "course,BSCS,BS Computer Science,,,,,,,\n"
    "subject,CS-101,Intro to Programming,BSCS,,,,,,\n"
    "instructor,,,,EMP-001,ana.cruz@school.edu,ChangeMe123!,Ana,Cruz,CS-101\n"
)


def _upload(client, headers, text, path="/admin/setup-import"):
    return client.post(
        path, headers=headers, files={"file": ("setup.csv", text.encode("utf-8"), "text/csv")}
    )


def test_preview_reports_what_would_be_created(client, make_user, make_role, auth_headers):
    make_role("instructor")  # roles are created lazily; an instructor row needs this one to exist
    admin = make_user("admin")

    response = _upload(client, auth_headers(admin), CSV, "/admin/setup-import/preview")

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["preview"] is True
    assert (body["created_courses"], body["created_subjects"], body["created_instructors"]) == (1, 1, 1)


def test_preview_writes_nothing(client, db, default_school, make_user, make_role, auth_headers):
    """The property the whole feature rests on. If this ever fails, "preview" silently became
    "import", and an admin checking their file would have imported it."""
    make_role("instructor")
    admin = make_user("admin")

    _upload(client, auth_headers(admin), CSV, "/admin/setup-import/preview")

    assert db.query(Course).filter(Course.code == "BSCS").first() is None
    assert db.query(Subject).filter(Subject.code == "CS-101").first() is None
    assert db.query(User).filter(User.email == "ana.cruz@school.edu").first() is None
    assert db.query(Instructor).filter(Instructor.employee_number == "EMP-001").first() is None


def test_previewing_twice_reports_the_same_thing(client, make_user, auth_headers):
    """A preview that consumed its own file would report 3 creations then 3 skips, which is the
    symptom of it having written after all."""
    admin = make_user("admin")
    headers = auth_headers(admin)

    first = _upload(client, headers, CSV, "/admin/setup-import/preview").json()
    second = _upload(client, headers, CSV, "/admin/setup-import/preview").json()

    assert first["created_courses"] == second["created_courses"] == 1
    assert first["skipped_existing"] == second["skipped_existing"] == 0


def test_preview_finds_the_duplicates_a_real_import_would_skip(
    client, db, default_school, make_user, make_role, auth_headers
):
    """The panel's actual ask: see duplicates before importing. This is only trustworthy because
    the count comes from the importer's own duplicate check, not a second implementation of it."""
    make_role("instructor")
    admin = make_user("admin")
    headers = auth_headers(admin)
    _upload(client, headers, CSV, "/admin/setup-import")  # for real

    preview = _upload(client, headers, CSV, "/admin/setup-import/preview").json()

    assert preview["skipped_existing"] == 3
    assert preview["created_courses"] == 0


def test_preview_reports_the_same_row_errors_as_an_import(client, make_user, auth_headers):
    bad = (
        "type,code,name,course_code,employee_number,email,password,first_name,last_name,subject_codes\n"
        "subject,CS-101,Orphan Subject,NOSUCHCOURSE,,,,,,\n"
    )
    admin = make_user("admin")

    preview = _upload(client, auth_headers(admin), bad, "/admin/setup-import/preview").json()

    assert len(preview["errors"]) == 1
    assert preview["errors"][0]["row"] == 2
    assert "NOSUCHCOURSE" in preview["errors"][0]["message"]


def test_one_bad_row_does_not_abandon_the_rest_of_a_preview(client, make_user, auth_headers):
    """The importer rolls back per bad row. Inside a preview that rollback has to unwind to the
    savepoint rather than to the outer transaction, or the first error would end the run."""
    mixed = (
        "type,code,name,course_code,employee_number,email,password,first_name,last_name,subject_codes\n"
        "course,BSCS,BS Computer Science,,,,,,,\n"
        "subject,CS-101,Orphan,NOSUCHCOURSE,,,,,,\n"
        "subject,CS-202,Data Structures,BSCS,,,,,,\n"
    )
    admin = make_user("admin")

    preview = _upload(client, auth_headers(admin), mixed, "/admin/setup-import/preview").json()

    assert preview["created_courses"] == 1
    assert preview["created_subjects"] == 1
    assert len(preview["errors"]) == 1


def test_a_real_import_is_not_marked_as_a_preview(client, make_user, make_role, auth_headers):
    make_role("instructor")
    admin = make_user("admin")

    body = _upload(client, auth_headers(admin), CSV, "/admin/setup-import").json()

    assert body["preview"] is False


def test_preview_is_admin_only(client, make_instructor, auth_headers):
    instructor = make_instructor()

    response = _upload(
        client, auth_headers(instructor.user), CSV, "/admin/setup-import/preview"
    )

    assert response.status_code == 403
