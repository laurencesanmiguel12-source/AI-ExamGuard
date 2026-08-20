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


def test_creating_an_exam_ignores_a_spoofed_instructor_id(
    client, make_instructor, make_subject, make_instructor_subject, auth_headers
):
    real_instructor = make_instructor()
    other_instructor = make_instructor()
    subject = make_subject()
    make_instructor_subject(real_instructor, subject)

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
        data={"event_type": "TAB_SWITCH"},  # Form fields now, not JSON - see routes/violation.py
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


# --- GET /exams/{exam_id}/questions: found while writing this test suite, not from a prior
# session's history like the vulnerabilities above. ANY authenticated user (no enrollment, no
# ownership) could pull any exam's questions INCLUDING is_correct on every choice - the answer
# key, before ever taking the exam. Fixed by scoping to exam ownership (instructor/admin) or real
# course eligibility (student, via the same ExamService.is_student_eligible check
# POST /exam-sessions/start already uses), and by stripping is_correct from what an eligible
# student sees UNLESS they've already submitted that exam - ResultDetail.jsx (the student's own
# post-exam review page) legitimately needs is_correct at that point, and it can no longer help
# them cheat on an exam they've already turned in.

def _add_question_with_a_correct_choice(client, headers, exam_id):
    q = client.post(f"/exams/{exam_id}/questions", headers=headers, json={
        "question_text": "2 + 2 = ?", "question_type": "MULTIPLE_CHOICE", "points": 10, "order_number": 1,
    }).json()
    client.post(f"/exams/{exam_id}/questions/{q['id']}/choices", headers=headers,
                json={"choice_text": "4", "is_correct": True})
    client.post(f"/exams/{exam_id}/questions/{q['id']}/choices", headers=headers,
                json={"choice_text": "5", "is_correct": False})
    return q["id"]


def test_ineligible_student_cannot_view_another_courses_exam_questions(client, make_instructor, make_student, make_exam, make_course, auth_headers):
    instructor = make_instructor()
    exam = make_exam(instructor=instructor)
    _add_question_with_a_correct_choice(client, auth_headers(instructor.user), exam.id)

    outsider = make_student(course=make_course())  # different course than the exam's subject

    response = client.get(f"/exams/{exam.id}/questions", headers=auth_headers(outsider.user))

    assert response.status_code == 403


def test_eligible_student_can_view_questions_but_not_yet_the_answer_key(client, make_instructor, make_student, make_exam, auth_headers):
    instructor = make_instructor()
    exam = make_exam(instructor=instructor)
    _add_question_with_a_correct_choice(client, auth_headers(instructor.user), exam.id)

    student = make_student(course=exam.subject.course, exam=exam)

    response = client.get(f"/exams/{exam.id}/questions", headers=auth_headers(student.user))

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert len(body[0]["choices"]) == 2
    for choice in body[0]["choices"]:
        assert "is_correct" not in choice


def test_student_mid_exam_still_does_not_see_the_answer_key(client, db, make_instructor, make_student, make_exam, auth_headers):
    instructor = make_instructor()
    exam = make_exam(instructor=instructor)
    _add_question_with_a_correct_choice(client, auth_headers(instructor.user), exam.id)

    student = make_student(course=exam.subject.course, exam=exam)
    _start_session(db, student, exam)  # IN_PROGRESS, not SUBMITTED

    response = client.get(f"/exams/{exam.id}/questions", headers=auth_headers(student.user))

    assert response.status_code == 200
    for choice in response.json()[0]["choices"]:
        assert "is_correct" not in choice


def test_student_who_already_submitted_can_see_the_answer_key_for_review(client, db, make_instructor, make_student, make_exam, auth_headers):
    instructor = make_instructor()
    exam = make_exam(instructor=instructor)
    _add_question_with_a_correct_choice(client, auth_headers(instructor.user), exam.id)

    student = make_student(course=exam.subject.course, exam=exam)
    session = _start_session(db, student, exam)
    session.status = "SUBMITTED"
    db.commit()

    response = client.get(f"/exams/{exam.id}/questions", headers=auth_headers(student.user))

    assert response.status_code == 200
    choices = response.json()[0]["choices"]
    assert any(c["is_correct"] is True for c in choices)


def test_non_owner_instructor_cannot_view_someone_elses_exam_questions(client, make_instructor, make_exam, auth_headers):
    owner = make_instructor()
    other = make_instructor()
    exam = make_exam(instructor=owner)
    _add_question_with_a_correct_choice(client, auth_headers(owner.user), exam.id)

    response = client.get(f"/exams/{exam.id}/questions", headers=auth_headers(other.user))

    assert response.status_code == 403


def test_owning_instructor_sees_is_correct(client, make_instructor, make_exam, auth_headers):
    instructor = make_instructor()
    exam = make_exam(instructor=instructor)
    _add_question_with_a_correct_choice(client, auth_headers(instructor.user), exam.id)

    response = client.get(f"/exams/{exam.id}/questions", headers=auth_headers(instructor.user))

    assert response.status_code == 200
    choices = response.json()[0]["choices"]
    assert any(c["is_correct"] is True for c in choices)
