"""Multi-tenancy: multiple schools share one deployment, each with its own admin/instructors/
courses/students, and none of it should ever be visible or editable across schools. Every one of
these was a real gap before school scoping was added (see ai_examguard_hosting_decision /
project_status memory) - either "any admin could touch any course" (there was only ever one admin
before) or a flat db.query(X).all() with zero scoping (ExamService.get_all, RiskService's live
monitor, audit log, retention)."""
from datetime import datetime, timedelta, timezone


def test_school_signup_creates_a_working_admin_account(client, make_role, make_user, auth_headers):
    make_role("admin")  # school signup is the first-ever admin-creating flow - no other fixture
    # in this test seeds the "admin" Role row first, unlike make_user("admin", ...) elsewhere.
    response = client.post("/schools/register", json={
        "code": "NEWU",
        "name": "New University",
        "slug": "new-university",
        "email": "admin@newu.example.com",
        "password": "TestPass123!",
        "first_name": "New",
        "last_name": "Admin",
    })
    assert response.status_code == 200
    assert response.json()["status"] == "pending"

    # Signup alone no longer grants access - a super admin reviews it first.
    blocked = client.post("/auth/login", json={
        "email": "admin@newu.example.com",
        "password": "TestPass123!",
    })
    assert blocked.status_code == 403
    assert "pending review" in blocked.json()["detail"]

    super_admin = make_user("super_admin")
    approved = client.put(
        f"/schools/{response.json()['id']}/review",
        headers=auth_headers(super_admin),
        json={"status": "approved"},
    )
    assert approved.status_code == 200

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


def test_admin_cannot_fetch_another_schools_session_by_id(
    client, db, make_exam, make_student, make_user, make_school, auth_headers
):
    """require_session_read_access's admin branch had zero school check - any admin could read
    any other school's exam session by id, same leak pattern already fixed elsewhere in this
    file for the list endpoint but missed here."""
    from app.models.exam_session import ExamSession

    school_a = make_school()
    admin_a = make_user("admin", school=school_a)

    other_exam = make_exam()  # default_school
    other_student = make_student(course=other_exam.subject.course)
    session = ExamSession(
        student_id=other_student.id, exam_id=other_exam.id,
        started_at=datetime.now(timezone.utc), status="IN_PROGRESS",
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    response = client.get(f"/exam-sessions/{session.id}", headers=auth_headers(admin_a))
    assert response.status_code == 404


def test_admin_cannot_delete_another_schools_session(
    client, db, make_exam, make_student, make_user, make_school, auth_headers
):
    """require_session_manage_access's admin branch had zero school check - any admin could
    delete (and cascade-erase the violations of) any other school's exam session."""
    from app.models.exam_session import ExamSession

    school_a = make_school()
    admin_a = make_user("admin", school=school_a)

    other_exam = make_exam()  # default_school
    other_student = make_student(course=other_exam.subject.course)
    session = ExamSession(
        student_id=other_student.id, exam_id=other_exam.id,
        started_at=datetime.now(timezone.utc), status="IN_PROGRESS",
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    response = client.delete(f"/exam-sessions/{session.id}", headers=auth_headers(admin_a))
    assert response.status_code == 404


def test_admin_cannot_view_another_schools_violation_evidence(
    client, db, make_exam, make_student, make_user, make_school, auth_headers
):
    """require_violation_read_access's admin branch had zero school check - any admin could view
    any other school's violation, including its evidence photo."""
    from app.models.exam_session import ExamSession
    from app.models.violation import Violation

    school_a = make_school()
    admin_a = make_user("admin", school=school_a)

    other_exam = make_exam()  # default_school
    other_student = make_student(course=other_exam.subject.course)
    session = ExamSession(
        student_id=other_student.id, exam_id=other_exam.id,
        started_at=datetime.now(timezone.utc), status="IN_PROGRESS",
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    violation = Violation(exam_session_id=session.id, event_type="PHONE_DETECTED")
    db.add(violation)
    db.commit()
    db.refresh(violation)

    response = client.get(f"/violations/{violation.id}/evidence", headers=auth_headers(admin_a))
    assert response.status_code == 404


def test_admin_cannot_review_another_schools_violation_appeal(
    client, db, make_exam, make_student, make_user, make_school, auth_headers
):
    """require_violation_manage_access's admin branch had zero school check - any admin could
    approve or reject appeals filed by any other school's students."""
    from app.models.exam_session import ExamSession
    from app.models.violation import Violation

    school_a = make_school()
    admin_a = make_user("admin", school=school_a)

    other_exam = make_exam()  # default_school
    other_student = make_student(course=other_exam.subject.course)
    session = ExamSession(
        student_id=other_student.id, exam_id=other_exam.id,
        started_at=datetime.now(timezone.utc), status="IN_PROGRESS",
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    violation = Violation(
        exam_session_id=session.id, event_type="PHONE_DETECTED",
        appeal_status="PENDING", appeal_reason="not me",
    )
    db.add(violation)
    db.commit()
    db.refresh(violation)

    response = client.put(
        f"/violations/{violation.id}/appeal-review", headers=auth_headers(admin_a),
        json={"status": "UPHELD", "response": "denied"},
    )
    assert response.status_code == 404


# --- super admin: the intentional exception to every school check above ---

def test_super_admin_can_read_another_schools_session(
    client, db, make_exam, make_student, make_user, auth_headers
):
    """The whole point of super_admin - unlike test_admin_cannot_fetch_another_schools_session_by_id,
    this should succeed regardless of which school the session belongs to."""
    from app.models.exam_session import ExamSession

    super_admin = make_user("super_admin")  # belongs to default_school - irrelevant to its access

    other_exam = make_exam()  # a different (default) school in practice, but doesn't matter here
    other_student = make_student(course=other_exam.subject.course)
    session = ExamSession(
        student_id=other_student.id, exam_id=other_exam.id,
        started_at=datetime.now(timezone.utc), status="IN_PROGRESS",
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    response = client.get(f"/exam-sessions/{session.id}", headers=auth_headers(super_admin))
    assert response.status_code == 200


def test_super_admin_can_review_another_schools_violation_appeal(
    client, db, make_exam, make_student, make_user, auth_headers
):
    from app.models.exam_session import ExamSession
    from app.models.violation import Violation

    super_admin = make_user("super_admin")

    other_exam = make_exam()
    other_student = make_student(course=other_exam.subject.course)
    session = ExamSession(
        student_id=other_student.id, exam_id=other_exam.id,
        started_at=datetime.now(timezone.utc), status="IN_PROGRESS",
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    violation = Violation(
        exam_session_id=session.id, event_type="PHONE_DETECTED",
        appeal_status="PENDING", appeal_reason="not me",
    )
    db.add(violation)
    db.commit()
    db.refresh(violation)

    response = client.put(
        f"/violations/{violation.id}/appeal-review", headers=auth_headers(super_admin),
        json={"status": "UPHELD", "response": "denied"},
    )
    assert response.status_code == 200


def test_super_admin_sees_students_from_every_school(
    client, db, make_student, make_course, make_user, make_school, auth_headers
):
    school_b = make_school()
    super_admin = make_user("super_admin")
    student_b = make_student(course=make_course(school=school_b))
    db.commit()

    response = client.get("/students/", headers=auth_headers(super_admin))
    assert response.status_code == 200
    student_ids = {s["id"] for s in response.json()}
    assert student_b.id in student_ids


def test_regular_admin_cannot_list_platform_users(client, make_user, auth_headers):
    admin = make_user("admin")
    response = client.get("/admin/users/", headers=auth_headers(admin))
    assert response.status_code == 403


def test_super_admin_can_list_platform_users(client, make_user, auth_headers):
    super_admin = make_user("super_admin")
    other = make_user("instructor")

    response = client.get("/admin/users/", headers=auth_headers(super_admin))
    assert response.status_code == 200
    user_ids = {u["id"] for u in response.json()}
    assert other.id in user_ids


def test_super_admin_can_change_a_users_role(client, make_user, make_role, auth_headers):
    make_role("admin")  # roles are lazily created on demand - "admin" isn't touched otherwise here
    super_admin = make_user("super_admin")
    target = make_user("instructor")

    response = client.put(
        f"/admin/users/{target.id}/role", headers=auth_headers(super_admin),
        json={"role_name": "admin"},
    )
    assert response.status_code == 200
    assert response.json()["role_name"] == "admin"


def test_super_admin_cannot_change_their_own_role(client, make_user, auth_headers):
    super_admin = make_user("super_admin")

    response = client.put(
        f"/admin/users/{super_admin.id}/role", headers=auth_headers(super_admin),
        json={"role_name": "admin"},
    )
    assert response.status_code == 400


def test_cannot_demote_a_schools_only_admin(client, make_user, make_role, make_school, auth_headers):
    """EARIST (school 11) reached zero admins in production, which is unrecoverable through the
    UI - every management route is require_admin and the only admin-creating endpoint is
    super-admin-only. The school keeps its admin unless another one exists first."""
    make_role("instructor")  # roles are lazily created on demand - the demote target must exist
    super_admin = make_user("super_admin")
    school_b = make_school()
    only_admin = make_user("admin", school=school_b)

    response = client.put(
        f"/admin/users/{only_admin.id}/role", headers=auth_headers(super_admin),
        json={"role_name": "instructor"},
    )
    assert response.status_code == 400
    assert "only admin" in response.json()["detail"]


def test_promoting_a_schools_only_admin_to_super_admin_is_also_blocked(
    client, make_user, make_school, auth_headers
):
    """A super admin isn't school-scoped, so moving the last admin up still leaves the school
    with nobody who can administer it - the guard is about the school's admin slot, not about
    demotion specifically."""
    super_admin = make_user("super_admin")
    school_b = make_school()
    only_admin = make_user("admin", school=school_b)

    response = client.put(
        f"/admin/users/{only_admin.id}/role", headers=auth_headers(super_admin),
        json={"role_name": "super_admin"},
    )
    assert response.status_code == 400


def test_can_demote_an_admin_when_the_school_has_another_one(
    client, make_user, make_role, make_school, auth_headers
):
    make_role("instructor")  # roles are lazily created on demand - the demote target must exist
    super_admin = make_user("super_admin")
    school_b = make_school()
    make_user("admin", school=school_b, email="kept_admin@example.com")
    spare_admin = make_user("admin", school=school_b, email="spare_admin@example.com")

    response = client.put(
        f"/admin/users/{spare_admin.id}/role", headers=auth_headers(super_admin),
        json={"role_name": "instructor"},
    )
    assert response.status_code == 200
    assert response.json()["role_name"] == "instructor"


def test_regular_admin_cannot_change_a_users_role(client, make_user, auth_headers):
    admin = make_user("admin")
    target = make_user("instructor")

    response = client.put(
        f"/admin/users/{target.id}/role", headers=auth_headers(admin),
        json={"role_name": "admin"},
    )
    assert response.status_code == 403


def test_super_admin_can_create_an_admin_for_any_school(client, make_user, make_role, make_school, auth_headers):
    make_role("admin")  # roles are lazily created on demand - "admin" isn't touched otherwise here
    super_admin = make_user("super_admin")
    school_b = make_school()

    response = client.post(
        "/admin/users/", headers=auth_headers(super_admin),
        json={
            "email": "new_admin_b@example.com", "password": "TestPass123!",
            "first_name": "New", "last_name": "Admin", "role_name": "admin", "school_id": school_b.id,
        },
    )
    assert response.status_code == 200
    assert response.json()["school_id"] == school_b.id
    assert response.json()["role_name"] == "admin"


def test_super_admin_can_deactivate_a_school_and_its_admin_is_blocked_from_login(
    client, make_user, make_school, auth_headers
):
    """make_user defaults every account to the real known TEST_PASSWORD ("TestPass123!") - same
    password test_auth.py's own login tests rely on - so this can log in for real before/after
    deactivating, rather than only checking the PUT response."""
    super_admin = make_user("super_admin")
    school_b = make_school()
    admin_b = make_user("admin", school=school_b, email="admin_b@example.com")

    pre_login = client.post("/auth/login", json={
        "email": "admin_b@example.com", "password": "TestPass123!",
    })
    assert pre_login.status_code == 200

    deactivate = client.put(
        f"/schools/{school_b.id}", headers=auth_headers(super_admin),
        json={"is_active": False},
    )
    assert deactivate.status_code == 200
    assert deactivate.json()["is_active"] is False

    post_login = client.post("/auth/login", json={
        "email": "admin_b@example.com", "password": "TestPass123!",
    })
    assert post_login.status_code == 403
