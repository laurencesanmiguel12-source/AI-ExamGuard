"""Regression tests for the dead end a freshly created instructor landed in, reported live as
"newly created instructor cannot see student roster" (2026-09-02).

The chain was: POST /instructors/ created the account with no subject assignment -> without one,
ExamService._require_subject_assignment 403s every exam creation -> owning no exams,
require_exam_owner 403s every roster. Meanwhile GET /exams/ returned the whole school's exams to
that instructor and Exams.jsx put a "View roster" link on every row, so the account saw a full
exam list where every roster link denied them.
"""


def test_instructor_exam_list_only_shows_their_own_exams(
    client, make_instructor, make_exam, make_subject, auth_headers
):
    subject = make_subject()
    mine = make_instructor()
    theirs = make_instructor()
    my_exam = make_exam(instructor=mine, subject=subject)
    make_exam(instructor=theirs, subject=subject)

    response = client.get("/exams/", headers=auth_headers(mine.user))

    assert response.status_code == 200
    assert [e["id"] for e in response.json()] == [my_exam.id]


def test_admin_exam_list_still_shows_the_whole_school(
    client, make_user, make_instructor, make_exam, make_subject, auth_headers
):
    """The scoping is instructor-only - an admin manages every exam in their school."""
    admin = make_user("admin")
    subject = make_subject()
    exam_a = make_exam(instructor=make_instructor(), subject=subject)
    exam_b = make_exam(instructor=make_instructor(), subject=subject)

    response = client.get("/exams/", headers=auth_headers(admin))

    assert response.status_code == 200
    assert {e["id"] for e in response.json()} >= {exam_a.id, exam_b.id}


def test_instructor_with_no_profile_row_gets_an_empty_exam_list(
    client, make_user, make_exam, auth_headers
):
    """role="instructor" with no linked Instructor row - what deleting an instructor used to
    leave behind. Empty list, not someone else's exams and not a 500."""
    make_exam()
    orphan = make_user("instructor")

    response = client.get("/exams/", headers=auth_headers(orphan))

    assert response.status_code == 200
    assert response.json() == []


def test_creating_an_instructor_can_assign_subjects_up_front(
    client, make_user, make_role, make_subject, auth_headers
):
    make_role("instructor")  # lazily created - create_user_account 500s without it
    admin = make_user("admin")
    subject = make_subject()

    response = client.post("/instructors/", headers=auth_headers(admin), json={
        "employee_number": "EMP-NEW-1",
        "email": "brand_new@example.com",
        "password": "TestPass123!",
        "first_name": "Brand",
        "last_name": "New",
        "subject_ids": [subject.id],
    })
    assert response.status_code == 200

    listed = client.get(
        f"/instructors/{response.json()['id']}/subjects", headers=auth_headers(admin)
    )
    assert listed.status_code == 200
    assert [row["subject_id"] for row in listed.json()] == [subject.id]


def test_creating_an_instructor_rejects_another_schools_subject(
    client, make_user, make_role, make_school, make_course, make_subject, auth_headers
):
    make_role("instructor")  # lazily created - create_user_account 500s without it
    admin = make_user("admin")
    other_school = make_school()
    foreign_subject = make_subject(course=make_course(school=other_school))

    response = client.post("/instructors/", headers=auth_headers(admin), json={
        "employee_number": "EMP-NEW-2",
        "email": "cross_tenant@example.com",
        "password": "TestPass123!",
        "first_name": "Cross",
        "last_name": "Tenant",
        "subject_ids": [foreign_subject.id],
    })

    assert response.status_code == 403


def test_subject_ids_is_optional(client, make_user, make_role, auth_headers):
    """Old clients that don't send the field must keep working."""
    make_role("instructor")  # lazily created - create_user_account 500s without it
    admin = make_user("admin")

    response = client.post("/instructors/", headers=auth_headers(admin), json={
        "employee_number": "EMP-NEW-3",
        "email": "no_subjects@example.com",
        "password": "TestPass123!",
        "first_name": "No",
        "last_name": "Subjects",
    })

    assert response.status_code == 200


def test_deleting_an_instructor_removes_their_login_too(
    client, db, make_user, make_instructor, auth_headers
):
    from app.models.user import User

    admin = make_user("admin")
    instructor = make_instructor()
    user_id = instructor.user.id

    response = client.delete(f"/instructors/{instructor.id}", headers=auth_headers(admin))

    assert response.status_code == 200
    assert db.query(User).filter(User.id == user_id).first() is None


def test_cannot_delete_an_instructor_who_still_owns_exams(
    client, make_user, make_instructor, make_exam, auth_headers
):
    """Used to surface as an IntegrityError 500 - exams.instructor_id has no ON DELETE."""
    admin = make_user("admin")
    instructor = make_instructor()
    make_exam(instructor=instructor)

    response = client.delete(f"/instructors/{instructor.id}", headers=auth_headers(admin))

    assert response.status_code == 400
    assert "still owns" in response.json()["detail"]
