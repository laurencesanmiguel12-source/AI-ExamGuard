"""Regression tests for the two real auth/ownership vulnerabilities found and fixed in this
project's history (see ai_examguard_project_status memory, commits 1140a16 and ee8aceb):

1. `POST /exams` used to trust `instructor_id` straight from the request body - any instructor
   could create an exam "as" another instructor. Fixed by deriving it from the caller's own linked
   Instructor record instead.
2. Every session_id/student_id-scoped route (violations, exam-session GET/PUT/DELETE, answers, ...)
   had NO ownership check at all - any authenticated user could read or tamper with any other
   student's exam session. Fixed with require_session_owner_student/read_access/manage_access.

These are exactly the kind of regressions a real test suite exists to catch - if either of these
were reintroduced, the fix would silently disappear again without a test failing to say so.
"""
from datetime import datetime, timedelta, timezone


def test_creating_an_exam_ignores_a_spoofed_instructor_id(client, make_instructor, make_subject, auth_headers):
    real_instructor = make_instructor()
    other_instructor = make_instructor()
    subject = make_subject()

    response = client.post("/exams/", headers=auth_headers(real_instructor.user), json={
        "title": "Spoof Attempt",
        "duration_minutes": 30,
        "passing_score": 50,
        "start_time": datetime.now(timezone.utc).isoformat(),
        "end_time": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
        "subject_id": subject.id,
        "instructor_id": other_instructor.id,  # attacker-controlled, must be ignored
    })

    assert response.status_code == 200
    assert response.json()["instructor_id"] == real_instructor.id
    assert response.json()["instructor_id"] != other_instructor.id


def test_instructor_cannot_edit_another_instructors_exam(client, make_instructor, make_exam, auth_headers):
    owner = make_instructor()
    attacker = make_instructor()
    exam = make_exam(instructor=owner)

    response = client.put(f"/exams/{exam.id}", headers=auth_headers(attacker.user), json={
        "title": "Hijacked",
    })

    assert response.status_code == 403


def test_instructor_cannot_delete_another_instructors_exam(client, make_instructor, make_exam, auth_headers):
    owner = make_instructor()
    attacker = make_instructor()
    exam = make_exam(instructor=owner)

    response = client.delete(f"/exams/{exam.id}", headers=auth_headers(attacker.user))

    assert response.status_code == 403


def test_instructor_can_edit_their_own_exam(client, make_instructor, make_exam, auth_headers):
    owner = make_instructor()
    exam = make_exam(instructor=owner)

    response = client.put(f"/exams/{exam.id}", headers=auth_headers(owner.user), json={
        "title": "Updated Title",
    })

    assert response.status_code == 200
    assert response.json()["title"] == "Updated Title"


def _start_session(db, student, exam):
    from app.models.exam_session import ExamSession
    session = ExamSession(
        student_id=student.id,
        exam_id=exam.id,
        started_at=datetime.now(timezone.utc),
        status="IN_PROGRESS",
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def test_student_cannot_read_another_students_session(client, db, make_student, make_exam, auth_headers):
    owner = make_student()
    attacker = make_student()
    exam = make_exam()
    session = _start_session(db, owner, exam)

    response = client.get(f"/exam-sessions/{session.id}", headers=auth_headers(attacker.user))

    assert response.status_code == 403


def test_student_cannot_submit_another_students_session(client, db, make_student, make_exam, auth_headers):
    owner = make_student()
    attacker = make_student()
    exam = make_exam()
    session = _start_session(db, owner, exam)

    response = client.put(f"/exam-sessions/submit/{session.id}", headers=auth_headers(attacker.user))

    assert response.status_code == 403


def test_student_cannot_log_a_violation_on_another_students_session(client, db, make_student, make_exam, auth_headers):
    owner = make_student()
    attacker = make_student()
    exam = make_exam()
    session = _start_session(db, owner, exam)

    response = client.post(
        f"/exam-sessions/{session.id}/violations",
        headers=auth_headers(attacker.user),
        json={"event_type": "TAB_SWITCH"},
    )

    assert response.status_code == 403


def test_student_can_read_their_own_session(client, db, make_student, make_exam, auth_headers):
    student = make_student()
    exam = make_exam()
    session = _start_session(db, student, exam)

    response = client.get(f"/exam-sessions/{session.id}", headers=auth_headers(student.user))

    assert response.status_code == 200
    assert response.json()["id"] == session.id


def test_instructor_can_read_a_session_for_their_own_exam(client, db, make_student, make_instructor, make_exam, auth_headers):
    instructor = make_instructor()
    exam = make_exam(instructor=instructor)
    student = make_student()
    session = _start_session(db, student, exam)

    response = client.get(f"/exam-sessions/{session.id}", headers=auth_headers(instructor.user))

    assert response.status_code == 200


def test_instructor_cannot_read_a_session_for_someone_elses_exam(client, db, make_student, make_instructor, make_exam, auth_headers):
    exam_owner = make_instructor()
    other_instructor = make_instructor()
    exam = make_exam(instructor=exam_owner)
    student = make_student()
    session = _start_session(db, student, exam)

    response = client.get(f"/exam-sessions/{session.id}", headers=auth_headers(other_instructor.user))

    assert response.status_code == 403


def test_admin_can_read_any_session(client, db, make_student, make_exam, make_user, auth_headers):
    student = make_student()
    exam = make_exam()
    session = _start_session(db, student, exam)
    admin_user = make_user("admin")

    response = client.get(f"/exam-sessions/{session.id}", headers=auth_headers(admin_user))

    assert response.status_code == 200


def test_reading_a_session_without_auth_is_rejected(client, db, make_student, make_exam):
    student = make_student()
    exam = make_exam()
    session = _start_session(db, student, exam)

    response = client.get(f"/exam-sessions/{session.id}")

    assert response.status_code in (401, 403)


def test_reading_a_nonexistent_session_is_404_not_403(client, make_student, auth_headers):
    student = make_student()
    response = client.get("/exam-sessions/999999", headers=auth_headers(student.user))
    assert response.status_code == 404
