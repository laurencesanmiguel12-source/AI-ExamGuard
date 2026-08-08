"""Multi-tenancy: multiple schools share one deployment, each with its own admin/instructors/
courses/students, and none of it should ever be visible or editable across schools. Every one of
these was a real gap before school scoping was added (see ai_examguard_hosting_decision /
project_status memory) - either "any admin could touch any course" (there was only ever one admin
before) or a flat db.query(X).all() with zero scoping (ExamService.get_all, RiskService's live
monitor, audit log, retention)."""
from datetime import datetime, timedelta, timezone


def test_school_signup_creates_a_working_admin_account(client, make_role):
    make_role("admin")  # school signup is the first-ever admin-creating flow - no other fixture
    # in this test seeds the "admin" Role row first, unlike make_user("admin", ...) elsewhere.
    response = client.post("/schools/register", json={
        "code": "NEWU",
        "name": "New University",
        "slug": "new-university",
        "username": "newu_admin",
        "email": "admin@newu.example.com",
        "password": "TestPass123!",
        "first_name": "New",
        "last_name": "Admin",
    })
    assert response.status_code == 200

    login = client.post("/auth/login", json={
        "email": "admin@newu.example.com",
        "password": "TestPass123!",
    })
    assert login.status_code == 200
    token = login.json()["access_token"]

    me = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.json()["role_name"] == "admin"

    create_course = client.post(
        "/courses/",
        headers={"Authorization": f"Bearer {token}"},
        json={"code": "BSCS", "name": "BS Computer Science"},
    )
    assert create_course.status_code == 200
    assert create_course.json()["school_id"] == response.json()["id"]


def test_admin_cannot_edit_another_schools_course(client, make_user, make_course, make_school, auth_headers):
    school_b = make_school()
    admin_a = make_user("admin")
    course_b = make_course(school=school_b)

    response = client.put(
        f"/courses/{course_b.id}", headers=auth_headers(admin_a), json={"name": "Hijacked"}
    )
    assert response.status_code == 403


def test_admin_cannot_delete_another_schools_course(client, make_user, make_course, make_school, auth_headers):
    school_b = make_school()
    admin_a = make_user("admin")
    course_b = make_course(school=school_b)

    response = client.delete(f"/courses/{course_b.id}", headers=auth_headers(admin_a))
    assert response.status_code == 403


def test_course_codes_can_collide_across_different_schools(client, make_user, make_course, make_school, auth_headers):
    """Same course code at two different schools is normal, not a collision - see Course's
    per-school UniqueConstraint (uq_course_school_code)."""
    school_b = make_school()
    admin_a = make_user("admin")
    make_course(school=school_b, code="BSCS")

    response = client.post(
        "/courses/", headers=auth_headers(admin_a), json={"code": "BSCS", "name": "BS Computer Science"}
    )
    assert response.status_code == 200


def test_course_list_is_scoped_to_the_callers_school(client, make_user, make_course, make_school, auth_headers):
    school_a = make_school()
    school_b = make_school()
    admin_a = make_user("admin", school=school_a)
    course_a = make_course(school=school_a)
    make_course(school=school_b)  # a different school's course - must never appear below

    response = client.get("/courses/", params={"school_id": school_a.id}, headers=auth_headers(admin_a))
    assert response.status_code == 200
    ids = {c["id"] for c in response.json()}
    assert ids == {course_a.id}


def test_instructor_list_is_scoped_to_the_callers_school(client, make_instructor, make_user, make_school, auth_headers):
    school_b = make_school()
    admin_a = make_user("admin")
    make_instructor(user=make_user("instructor", school=school_b))

    response = client.get("/instructors/", headers=auth_headers(admin_a))
    assert response.status_code == 200
    assert response.json() == []


def test_student_list_is_scoped_to_the_callers_school(client, make_student, make_user, make_school, auth_headers):
    school_b = make_school()
    admin_a = make_user("admin")
    make_student(user=make_user("student", school=school_b))

    response = client.get("/students/", headers=auth_headers(admin_a))
    assert response.status_code == 200
    assert response.json() == []


def test_subject_list_is_scoped_to_the_callers_school(client, make_subject, make_course, make_user, make_school, auth_headers):
    school_a = make_school()
    school_b = make_school()
    admin_a = make_user("admin", school=school_a)
    subject_a = make_subject(course=make_course(school=school_a))
    make_subject(course=make_course(school=school_b))

    response = client.get("/subjects/", headers=auth_headers(admin_a))
    assert response.status_code == 200
    ids = {s["id"] for s in response.json()}
    assert ids == {subject_a.id}


def test_instructor_subject_assignment_rejects_cross_school_pair(
    client, make_instructor, make_subject, make_course, make_user, make_school, auth_headers
):
    school_a = make_school()
    school_b = make_school()
    admin_a = make_user("admin", school=school_a)
    instructor_a = make_instructor(user=make_user("instructor", school=school_a))
    subject_b = make_subject(course=make_course(school=school_b))

    response = client.post(
        f"/instructors/{instructor_a.id}/subjects/",
        headers=auth_headers(admin_a),
        json={"subject_id": subject_b.id},
    )
    assert response.status_code == 403


def test_exam_list_never_shows_another_schools_exams(client, make_exam, make_user, make_school, auth_headers):
    school_a = make_school()
    school_b = make_school()
    admin_a = make_user("admin", school=school_a)
    exam_b = make_exam()  # default_school fixture puts this in a third, unrelated school

    response = client.get("/exams/", headers=auth_headers(admin_a))
    assert response.status_code == 200
    ids = {e["id"] for e in response.json()}
    assert exam_b.id not in ids


def test_live_sessions_never_shows_another_schools_session(
    client, db, make_exam, make_student, make_instructor, make_user, make_school, auth_headers
):
    school_a = make_school()
    instructor_a = make_instructor(user=make_user("instructor", school=school_a))

    other_exam = make_exam()  # a different (default) school
    other_student = make_student(course=other_exam.subject.course)
    from app.models.exam_session import ExamSession
    session = ExamSession(
        student_id=other_student.id, exam_id=other_exam.id,
        started_at=datetime.now(timezone.utc), status="IN_PROGRESS",
    )
    db.add(session)
    db.commit()

    response = client.get("/exam-sessions/live", headers=auth_headers(instructor_a.user))
    assert response.status_code == 200
    assert response.json()["sessions"] == []


def test_admin_cannot_fetch_another_schools_exam_by_id(client, make_exam, make_user, make_school, auth_headers):
    """get_by_id_for_user only ever checked eligibility for the student branch - an instructor or
    admin from any school could fetch any other school's exam by id with zero scoping."""
    school_a = make_school()
    admin_a = make_user("admin", school=school_a)
    exam_b = make_exam()  # default_school - a different school from school_a

    response = client.get(f"/exams/{exam_b.id}", headers=auth_headers(admin_a))
    assert response.status_code == 404


def test_admin_cannot_view_another_schools_exam_answer_key(
    client, make_instructor, make_exam, make_user, make_school, auth_headers
):
    """list_exam_questions' admin branch returned the full answer key (is_correct included) for
    any exam id with no school check at all."""
    school_a = make_school()
    admin_a = make_user("admin", school=school_a)
    instructor_b = make_instructor()  # default_school
    exam_b = make_exam(instructor=instructor_b)
    client.post(f"/exams/{exam_b.id}/questions", headers=auth_headers(instructor_b.user), json={
        "question_text": "Hijack me", "question_type": "MULTIPLE_CHOICE", "points": 10, "order_number": 1,
    })

    response = client.get(f"/exams/{exam_b.id}/questions", headers=auth_headers(admin_a))
    assert response.status_code == 404


def test_exam_sessions_admin_list_is_scoped_to_the_callers_school(
    client, db, make_exam, make_student, make_user, make_school, auth_headers
):
    """ExamSessionService.get_all's admin branch was a bare db.query(ExamSession).all() -
    every session in the deployment, regardless of school."""
    school_a = make_school()
    admin_a = make_user("admin", school=school_a)

    other_exam = make_exam()  # default_school
    other_student = make_student(course=other_exam.subject.course)
    from datetime import datetime, timezone
    from app.models.exam_session import ExamSession
    session = ExamSession(
        student_id=other_student.id, exam_id=other_exam.id,
        started_at=datetime.now(timezone.utc), status="IN_PROGRESS",
    )
    db.add(session)
    db.commit()

    response = client.get("/exam-sessions/", headers=auth_headers(admin_a))
    assert response.status_code == 200
    assert response.json() == []


def test_audit_log_is_scoped_to_the_callers_school(client, db, make_user, make_school, auth_headers):
    school_b = make_school()
    admin_a = make_user("admin")
    actor_b = make_user("admin", school=school_b)

    from app.services.audit_log_service import AuditLogService
    AuditLogService.log(actor_b.id, "VIEW_EVIDENCE", "violation", 1, db, detail="school B action")
    db.commit()

    response = client.get("/admin/audit-log", headers=auth_headers(admin_a))
    assert response.status_code == 200
    assert response.json() == []
