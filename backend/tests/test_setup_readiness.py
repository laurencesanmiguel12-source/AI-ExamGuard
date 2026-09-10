"""The setup readiness report.

The panel asked that bulk import be able to link instructors to what it creates, "or
alternatively, it can be left floating then add a workflow to connect them". Once exams hang off
sections, connecting them stops meaning instructor-to-subject and starts meaning the whole chain:
a subject somebody teaches, opened as a class this term, with students enrolled in it.

These tests pin that the report walks that chain in order and names the FIRST unmet step - the
difference between a checklist and six things to choose between.
"""
from datetime import date

from app.services.academic_service import AcademicService


def _year_and_term(db, school_id, activate=True):
    year = AcademicService.create_year(
        "2026-2027", date(2026, 6, 1), date(2027, 5, 31), True, school_id, db
    )
    term = AcademicService.create_term(
        year.id, "1st Semester", 1, date(2026, 6, 1), date(2026, 10, 31), school_id, db
    )
    if activate:
        term = AcademicService.set_term_status(term.id, "ACTIVE", school_id, db)
    return year, term


def _get(client, auth_headers, admin):
    return client.get("/admin/setup-import/readiness", headers=auth_headers(admin)).json()


# --- the flow, in order -----------------------------------------------------------------------

def test_a_school_with_nothing_is_told_to_open_a_year_first(client, make_user, auth_headers):
    admin = make_user("admin")

    body = _get(client, auth_headers, admin)

    assert body["ready"] is False
    assert "school year" in body["blocking_step"].lower()


def test_a_year_with_no_running_term_is_the_next_step(client, db, default_school, make_user, auth_headers):
    _year_and_term(db, default_school.id, activate=False)
    admin = make_user("admin")

    body = _get(client, auth_headers, admin)

    assert body["current_year"] == "2026-2027"
    assert body["active_term"] is None
    assert "no term is running" in body["blocking_step"].lower()


def test_a_running_term_with_no_sections_names_that(
    client, db, default_school, make_user, auth_headers
):
    _year_and_term(db, default_school.id)
    admin = make_user("admin")

    body = _get(client, auth_headers, admin)

    assert body["active_term"] == "1st Semester"
    assert "no sections in 1st semester" in body["blocking_step"].lower()


def test_sections_with_nobody_in_them_are_the_last_thing_in_the_way(
    client, db, default_school, make_subject, make_instructor, make_user, auth_headers
):
    _, term = _year_and_term(db, default_school.id)
    AcademicService.create_section(
        make_subject(code="CS-101").id, term.id, make_instructor().id, "A", default_school.id, db
    )
    admin = make_user("admin")

    body = _get(client, auth_headers, admin)

    assert body["ready"] is False
    assert "every section is empty" in body["blocking_step"].lower()
    assert [i["label"] for i in body["sections_without_enrollment"]] == ["CS-101 A"]


def test_one_enrolled_class_is_enough_to_be_ready(
    client, db, default_school, make_subject, make_instructor, make_student, make_user, auth_headers
):
    """Ready means "a class could sit an exam today", not "everything is tidy" - a school with one
    live class and three other loose ends is running, and saying otherwise would be nagging."""
    _, term = _year_and_term(db, default_school.id)
    section = AcademicService.create_section(
        make_subject(code="CS-101").id, term.id, make_instructor().id, "A", default_school.id, db
    )
    AcademicService.enroll(section.id, [make_student().id], default_school.id, db)
    admin = make_user("admin")

    body = _get(client, auth_headers, admin)

    assert body["ready"] is True
    assert body["blocking_step"] is None


# --- the floating rows the panel asked about --------------------------------------------------

def test_an_instructor_imported_without_subjects_is_listed(
    client, make_instructor, make_user, auth_headers
):
    """Exactly the "left floating" case: an instructor row with an empty subject_codes cell."""
    floating = make_instructor()
    admin = make_user("admin")

    body = _get(client, auth_headers, admin)

    assert [i["id"] for i in body["instructors_without_subjects"]] == [floating.id]


def test_an_instructor_with_a_subject_is_not_listed(
    client, make_instructor, make_subject, make_instructor_subject, make_user, auth_headers
):
    instructor = make_instructor()
    make_instructor_subject(instructor, make_subject())
    admin = make_user("admin")

    body = _get(client, auth_headers, admin)

    assert body["instructors_without_subjects"] == []


def test_a_subject_nobody_teaches_is_listed(client, make_subject, make_user, auth_headers):
    subject = make_subject(code="CS-101", name="Intro")
    admin = make_user("admin")

    body = _get(client, auth_headers, admin)

    listed = body["subjects_without_instructor"]
    assert [i["id"] for i in listed] == [subject.id]
    assert listed[0]["label"] == "CS-101 Intro"


def test_subjects_not_opened_as_a_class_this_term_are_listed(
    client, db, default_school, make_subject, make_instructor, make_user, auth_headers
):
    """Assignment alone stopped being enough when exams moved onto sections. A subject somebody
    teaches but nobody opened as a class this term is the gap that replaced it."""
    _, term = _year_and_term(db, default_school.id)
    opened = make_subject(code="CS-101")
    unopened = make_subject(code="CS-202")
    AcademicService.create_section(
        opened.id, term.id, make_instructor().id, "A", default_school.id, db
    )
    admin = make_user("admin")

    body = _get(client, auth_headers, admin)

    assert [i["id"] for i in body["subjects_without_section"]] == [unopened.id]


def test_unopened_subjects_are_not_listed_before_a_term_exists(
    client, make_subject, make_user, auth_headers
):
    """With no term running there is nothing for a section to belong to, so listing every subject
    as "not opened" would be noise on a step nobody has reached."""
    make_subject(code="CS-101")
    admin = make_user("admin")

    body = _get(client, auth_headers, admin)

    assert body["subjects_without_section"] == []


# --- scoping ----------------------------------------------------------------------------------

def test_another_schools_loose_ends_are_not_reported(
    client, make_subject, make_course, make_school, make_user, auth_headers
):
    make_subject(course=make_course(school=make_school(name="Other University")))
    admin = make_user("admin")

    body = _get(client, auth_headers, admin)

    assert body["subjects_without_instructor"] == []


def test_readiness_is_admin_only(client, make_instructor, auth_headers):
    instructor = make_instructor()

    response = client.get(
        "/admin/setup-import/readiness", headers=auth_headers(instructor.user)
    )

    assert response.status_code == 403
