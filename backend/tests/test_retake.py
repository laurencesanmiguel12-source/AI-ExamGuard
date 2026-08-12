"""Risk-threshold retake flagging: submit_exam flags a session for instructor review when its
final risk score exceeds the exam's max_risk_score, start_exam blocks a new attempt until the
instructor grants or denies it, and an overturned appeal actually lowers the risk score it's
supposed to affect (see RiskService.score_violations's appeal_status filter)."""


def _log_violation(client, headers, session_id, event_type):
    response = client.post(
        f"/exam-sessions/{session_id}/violations",
        headers=headers,
        data={"event_type": event_type},
    )
    assert response.status_code == 200
    return response.json()


def test_submit_flags_retake_when_risk_exceeds_threshold(client, make_instructor, make_student, make_exam, auth_headers):
    instructor = make_instructor()
    exam = make_exam(instructor=instructor, total_points=0, passing_score=50, max_risk_score=30)
    student = make_student(course=exam.subject.course)
    student_headers = auth_headers(student.user)

    start = client.post("/exam-sessions/start", headers=student_headers, json={"exam_id": exam.id})
    session_id = start.json()["id"]

    # FULLSCREEN_EXIT(20) + TAB_SWITCH(15) = 35 > 30 threshold (see risk_service.py's WEIGHTS)
    _log_violation(client, student_headers, session_id, "FULLSCREEN_EXIT")
    _log_violation(client, student_headers, session_id, "TAB_SWITCH")

    submit = client.put(f"/exam-sessions/submit/{session_id}", headers=student_headers)
    assert submit.status_code == 200
    assert submit.json()["status"] == "FLAGGED_RETAKE"


def test_submit_does_not_flag_when_under_threshold(client, make_instructor, make_student, make_exam, auth_headers):
    exam = make_exam(total_points=0, passing_score=50, max_risk_score=30)
    student = make_student(course=exam.subject.course)
    student_headers = auth_headers(student.user)

    start = client.post("/exam-sessions/start", headers=student_headers, json={"exam_id": exam.id})
    session_id = start.json()["id"]

    _log_violation(client, student_headers, session_id, "TAB_SWITCH")  # 15, under 30

    submit = client.put(f"/exam-sessions/submit/{session_id}", headers=student_headers)
    assert submit.status_code == 200
    assert submit.json()["status"] == "SUBMITTED"


def test_retake_blocked_until_instructor_grants_it(client, make_instructor, make_student, make_exam, auth_headers):
    instructor = make_instructor()
    exam = make_exam(instructor=instructor, total_points=0, passing_score=50, max_risk_score=10)
    student = make_student(course=exam.subject.course)
    student_headers = auth_headers(student.user)
    instructor_headers = auth_headers(instructor.user)

    start = client.post("/exam-sessions/start", headers=student_headers, json={"exam_id": exam.id})
    session_id = start.json()["id"]
    _log_violation(client, student_headers, session_id, "TAB_SWITCH")  # 15 > 10
    client.put(f"/exam-sessions/submit/{session_id}", headers=student_headers)

    blocked = client.post("/exam-sessions/start", headers=student_headers, json={"exam_id": exam.id})
    assert blocked.status_code == 403

    grant = client.put(
        f"/exam-sessions/{session_id}/retake-review",
        headers=instructor_headers,
        json={"decision": "GRANT"},
    )
    assert grant.status_code == 200
    assert grant.json()["status"] == "RETAKE_GRANTED"

    retake = client.post("/exam-sessions/start", headers=student_headers, json={"exam_id": exam.id})
    assert retake.status_code == 200
    assert retake.json()["id"] != session_id


def test_retake_denied_permanently_blocks_a_new_attempt(client, make_instructor, make_student, make_exam, auth_headers):
    instructor = make_instructor()
    exam = make_exam(instructor=instructor, total_points=0, passing_score=50, max_risk_score=10)
    student = make_student(course=exam.subject.course)
    student_headers = auth_headers(student.user)
    instructor_headers = auth_headers(instructor.user)

    start = client.post("/exam-sessions/start", headers=student_headers, json={"exam_id": exam.id})
    session_id = start.json()["id"]
    _log_violation(client, student_headers, session_id, "TAB_SWITCH")
    client.put(f"/exam-sessions/submit/{session_id}", headers=student_headers)

    deny = client.put(
        f"/exam-sessions/{session_id}/retake-review",
        headers=instructor_headers,
        json={"decision": "DENY"},
    )
    assert deny.status_code == 200
    assert deny.json()["status"] == "RETAKE_DENIED"

    blocked = client.post("/exam-sessions/start", headers=student_headers, json={"exam_id": exam.id})
    assert blocked.status_code == 403


def test_non_owning_instructor_cannot_review_a_retake(client, make_instructor, make_student, make_exam, auth_headers):
    owner = make_instructor()
    other = make_instructor()
    exam = make_exam(instructor=owner, total_points=0, passing_score=50, max_risk_score=10)
    student = make_student(course=exam.subject.course)
    student_headers = auth_headers(student.user)

    start = client.post("/exam-sessions/start", headers=student_headers, json={"exam_id": exam.id})
    session_id = start.json()["id"]
    _log_violation(client, student_headers, session_id, "TAB_SWITCH")
    client.put(f"/exam-sessions/submit/{session_id}", headers=student_headers)

    response = client.put(
        f"/exam-sessions/{session_id}/retake-review",
        headers=auth_headers(other.user),
        json={"decision": "GRANT"},
    )
    assert response.status_code == 403


def test_flagged_retake_session_still_counts_as_a_graded_attempt_in_reports(
    client, make_instructor, make_student, make_exam, auth_headers
):
    """A FLAGGED_RETAKE session is still a real, scored, completed attempt - just also under risk
    review. It must not silently disappear from the instructor's report stats or leave the
    student unable to see their answer key on review (see GRADED_STATUSES)."""
    instructor = make_instructor()
    exam = make_exam(instructor=instructor, total_points=0, passing_score=50, max_risk_score=10)
    student = make_student(course=exam.subject.course)
    student_headers = auth_headers(student.user)
    instructor_headers = auth_headers(instructor.user)

    q = client.post(f"/exams/{exam.id}/questions", headers=instructor_headers, json={
        "question_text": "2 + 2 = ?", "question_type": "MULTIPLE_CHOICE", "points": 10, "order_number": 1,
    }).json()
    client.post(f"/exams/{exam.id}/questions/{q['id']}/choices", headers=instructor_headers,
                json={"choice_text": "4", "is_correct": True})

    start = client.post("/exam-sessions/start", headers=student_headers, json={"exam_id": exam.id})
    session_id = start.json()["id"]
    _log_violation(client, student_headers, session_id, "TAB_SWITCH")  # 15 > 10
    submit = client.put(f"/exam-sessions/submit/{session_id}", headers=student_headers)
    assert submit.json()["status"] == "FLAGGED_RETAKE"

    report = client.get(f"/exams/{exam.id}/report", headers=instructor_headers).json()
    assert report["submitted_count"] == 1
    assert report["in_progress_count"] == 0

    questions = client.get(f"/exams/{exam.id}/questions", headers=student_headers).json()
    assert any(c["is_correct"] is True for c in questions[0]["choices"])


def test_overturned_appeal_lowers_the_risk_score(client, make_instructor, make_student, make_exam, auth_headers):
    instructor = make_instructor()
    exam = make_exam(instructor=instructor, total_points=0, passing_score=50)
    student = make_student(course=exam.subject.course)
    student_headers = auth_headers(student.user)
    instructor_headers = auth_headers(instructor.user)

    start = client.post("/exam-sessions/start", headers=student_headers, json={"exam_id": exam.id})
    session_id = start.json()["id"]
    v1 = _log_violation(client, student_headers, session_id, "TAB_SWITCH")  # 15
    _log_violation(client, student_headers, session_id, "TAB_SWITCH")  # 15 -> 30 total

    before = client.get(f"/exam-sessions/{session_id}/risk-summary", headers=student_headers)
    assert before.json()["risk_score"] == 30

    appeal = client.post(
        f"/violations/{v1['id']}/appeal", headers=student_headers, json={"reason": "I didn't switch tabs."}
    )
    assert appeal.status_code == 200

    review = client.put(
        f"/violations/{v1['id']}/appeal-review",
        headers=instructor_headers,
        json={"status": "OVERTURNED", "response": "Confirmed a false positive."},
    )
    assert review.status_code == 200

    after = client.get(f"/exam-sessions/{session_id}/risk-summary", headers=student_headers)
    assert after.json()["risk_score"] == 15
