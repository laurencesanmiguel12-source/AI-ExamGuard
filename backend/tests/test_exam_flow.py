"""Exam content CRUD and the student-facing take-exam-and-get-scored flow. total_points is NOT
auto-synced from question points anywhere in the service layer (confirmed by reading
question_service.py) - tests that check scoring set it explicitly, matching what a real instructor
UI has to do too."""
from datetime import datetime, timezone


def _create_question_with_choices(client, headers, exam_id, points=10):
    q_resp = client.post(f"/exams/{exam_id}/questions", headers=headers, json={
        "question_text": "2 + 2 = ?",
        "question_type": "MULTIPLE_CHOICE",
        "points": points,
        "order_number": 1,
    })
    assert q_resp.status_code == 200
    question_id = q_resp.json()["id"]

    correct = client.post(f"/exams/{exam_id}/questions/{question_id}/choices", headers=headers, json={
        "choice_text": "4", "is_correct": True,
    }).json()
    wrong = client.post(f"/exams/{exam_id}/questions/{question_id}/choices", headers=headers, json={
        "choice_text": "5", "is_correct": False,
    }).json()
    return question_id, correct["id"], wrong["id"]


def test_create_question_and_choices(client, make_instructor, make_exam, auth_headers):
    instructor = make_instructor()
    exam = make_exam(instructor=instructor)
    headers = auth_headers(instructor.user)

    question_id, correct_id, wrong_id = _create_question_with_choices(client, headers, exam.id)

    listing = client.get(f"/exams/{exam.id}/questions", headers=headers)
    assert listing.status_code == 200
    body = listing.json()
    assert len(body) == 1
    assert len(body[0]["choices"]) == 2


def test_non_owner_instructor_cannot_add_questions(client, make_instructor, make_exam, auth_headers):
    owner = make_instructor()
    attacker = make_instructor()
    exam = make_exam(instructor=owner)

    response = client.post(f"/exams/{exam.id}/questions", headers=auth_headers(attacker.user), json={
        "question_text": "Hijacked question",
        "question_type": "MULTIPLE_CHOICE",
        "points": 10,
        "order_number": 1,
    })

    assert response.status_code == 403


def test_student_cannot_start_a_session_for_an_inactive_exam(client, make_student, make_exam, auth_headers):
    exam = make_exam(is_active=False)
    student = make_student(course=exam.subject.course)

    response = client.post("/exam-sessions/start", headers=auth_headers(student.user), json={
        "exam_id": exam.id,
    })

    assert response.status_code == 400


def test_student_cannot_start_two_sessions_for_the_same_exam(client, make_student, make_exam, auth_headers):
    exam = make_exam()
    student = make_student(course=exam.subject.course)
    headers = auth_headers(student.user)

    first = client.post("/exam-sessions/start", headers=headers, json={"exam_id": exam.id})
    assert first.status_code == 200

    second = client.post("/exam-sessions/start", headers=headers, json={"exam_id": exam.id})
    assert second.status_code == 400


def test_student_outside_the_exams_course_cannot_start_a_session(client, make_student, make_course, make_exam, auth_headers):
    exam = make_exam()
    other_course_student = make_student(course=make_course())

    response = client.post("/exam-sessions/start", headers=auth_headers(other_course_student.user), json={
        "exam_id": exam.id,
    })

    assert response.status_code == 403


def test_full_take_exam_flow_scores_correctly(client, make_instructor, make_student, make_exam, auth_headers):
    instructor = make_instructor()
    exam = make_exam(instructor=instructor, total_points=10, passing_score=50)
    instructor_headers = auth_headers(instructor.user)
    question_id, correct_id, wrong_id = _create_question_with_choices(client, instructor_headers, exam.id, points=10)

    student = make_student(course=exam.subject.course)
    student_headers = auth_headers(student.user)

    start = client.post("/exam-sessions/start", headers=student_headers, json={"exam_id": exam.id})
    assert start.status_code == 200
    session_id = start.json()["id"]

    answer = client.post(f"/exam-sessions/{session_id}/answers", headers=student_headers, json={
        "question_id": question_id,
        "choice_id": correct_id,
    })
    assert answer.status_code == 200
    assert answer.json()["is_correct"] is True
    assert answer.json()["points_awarded"] == 10

    submit = client.put(f"/exam-sessions/submit/{session_id}", headers=student_headers)
    assert submit.status_code == 200
    body = submit.json()
    assert body["status"] == "SUBMITTED"
    assert body["score"] == 10
    assert body["percentage"] == 100.0
    assert body["passed"] is True


def test_wrong_answer_fails_the_exam(client, make_instructor, make_student, make_exam, auth_headers):
    instructor = make_instructor()
    exam = make_exam(instructor=instructor, total_points=10, passing_score=50)
    instructor_headers = auth_headers(instructor.user)
    question_id, correct_id, wrong_id = _create_question_with_choices(client, instructor_headers, exam.id, points=10)

    student = make_student(course=exam.subject.course)
    student_headers = auth_headers(student.user)

    start = client.post("/exam-sessions/start", headers=student_headers, json={"exam_id": exam.id})
    session_id = start.json()["id"]

    client.post(f"/exam-sessions/{session_id}/answers", headers=student_headers, json={
        "question_id": question_id,
        "choice_id": wrong_id,
    })

    submit = client.put(f"/exam-sessions/submit/{session_id}", headers=student_headers)
    body = submit.json()
    assert body["score"] == 0
    assert body["percentage"] == 0.0
    assert body["passed"] is False


def test_cannot_submit_the_same_session_twice(client, make_instructor, make_student, make_exam, auth_headers):
    exam = make_exam()
    student = make_student(course=exam.subject.course)
    headers = auth_headers(student.user)

    start = client.post("/exam-sessions/start", headers=headers, json={"exam_id": exam.id})
    session_id = start.json()["id"]

    first_submit = client.put(f"/exam-sessions/submit/{session_id}", headers=headers)
    assert first_submit.status_code == 200

    second_submit = client.put(f"/exam-sessions/submit/{session_id}", headers=headers)
    assert second_submit.status_code == 400


def test_cannot_answer_after_submitting(client, make_instructor, make_student, make_exam, auth_headers):
    instructor = make_instructor()
    exam = make_exam(instructor=instructor)
    question_id, correct_id, _ = _create_question_with_choices(client, auth_headers(instructor.user), exam.id)

    student = make_student(course=exam.subject.course)
    headers = auth_headers(student.user)
    start = client.post("/exam-sessions/start", headers=headers, json={"exam_id": exam.id})
    session_id = start.json()["id"]
    client.put(f"/exam-sessions/submit/{session_id}", headers=headers)

    late_answer = client.post(f"/exam-sessions/{session_id}/answers", headers=headers, json={
        "question_id": question_id,
        "choice_id": correct_id,
    })
    assert late_answer.status_code == 400


# --- Violation evidence upload (extension screenshot capture, see extension/background.js) ---

def test_ai_tool_violation_with_evidence_is_retrievable(client, make_student, make_exam, auth_headers):
    exam = make_exam()
    student = make_student(course=exam.subject.course)
    headers = auth_headers(student.user)
    session_id = client.post("/exam-sessions/start", headers=headers, json={"exam_id": exam.id}).json()["id"]

    fake_screenshot = b"\xff\xd8\xff\xe0not a real jpeg but bytes are bytes for this test"
    response = client.post(
        f"/exam-sessions/{session_id}/violations",
        headers=headers,
        data={"event_type": "AI_TOOL_DETECTED", "detail": "chatgpt.com"},
        files={"evidence": ("evidence.jpg", fake_screenshot, "image/jpeg")},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["has_evidence"] is True

    evidence = client.get(f"/violations/{body['id']}/evidence", headers=headers)
    assert evidence.status_code == 200
    assert evidence.content == fake_screenshot


def test_ai_tool_violation_without_evidence_still_logs(client, make_student, make_exam, auth_headers):
    """The extension can't always capture a screenshot (background tab, permission gap, etc.) -
    the violation itself must still be logged even when no evidence file is attached."""
    exam = make_exam()
    student = make_student(course=exam.subject.course)
    headers = auth_headers(student.user)
    session_id = client.post("/exam-sessions/start", headers=headers, json={"exam_id": exam.id}).json()["id"]

    response = client.post(
        f"/exam-sessions/{session_id}/violations",
        headers=headers,
        data={"event_type": "AI_TOOL_DETECTED", "detail": "chatgpt.com"},
    )
    assert response.status_code == 200
    assert response.json()["has_evidence"] is False


def test_tab_switch_violation_never_has_evidence_even_if_sent(client, make_student, make_exam, auth_headers):
    """Purely behavioral events aren't in EVIDENCE_EVENT_TYPES - an evidence file attached to one
    anyway (shouldn't happen from real clients, but the server shouldn't trust the event_type
    label alone) is silently ignored, not stored."""
    exam = make_exam()
    student = make_student(course=exam.subject.course)
    headers = auth_headers(student.user)
    session_id = client.post("/exam-sessions/start", headers=headers, json={"exam_id": exam.id}).json()["id"]

    response = client.post(
        f"/exam-sessions/{session_id}/violations",
        headers=headers,
        data={"event_type": "TAB_SWITCH"},
        files={"evidence": ("evidence.jpg", b"irrelevant bytes", "image/jpeg")},
    )
    assert response.status_code == 200
    assert response.json()["has_evidence"] is False
