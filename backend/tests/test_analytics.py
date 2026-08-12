"""New /analytics endpoints: school-wide rollup for admin, cross-exam rollup for instructor.
Same cross-tenant concern as test_multi_tenancy.py's other list endpoints - a school-scoped
aggregate is only useful if it's actually scoped."""
from datetime import datetime, timezone


def test_school_analytics_scoped_to_callers_school(
    client, make_school, make_course, make_subject, make_instructor, make_user, make_exam, auth_headers
):
    school_a = make_school()
    admin_a = make_user("admin", school=school_a)
    instructor_a = make_instructor(user=make_user("instructor", school=school_a))
    # make_exam()'s default subject/course sit in the (unrelated) default_school fixture, same
    # gotcha test_multi_tenancy.py's exam tests call out - build one actually inside school_a.
    make_exam(instructor=instructor_a, subject=make_subject(course=make_course(school=school_a)))

    make_exam()  # default_school fixture - a different, unrelated school

    response = client.get("/analytics/school", headers=auth_headers(admin_a))
    assert response.status_code == 200
    body = response.json()
    assert body["total_exams"] == 1
    assert [i["instructor_id"] for i in body["instructors"]] == [instructor_a.id]


def test_instructor_analytics_only_includes_own_exams(
    client, make_instructor, make_exam, auth_headers
):
    instructor_a = make_instructor()
    exam_a = make_exam(instructor=instructor_a)
    make_exam()  # a different instructor's exam - must never appear below

    response = client.get("/analytics/instructor", headers=auth_headers(instructor_a.user))
    assert response.status_code == 200
    body = response.json()
    assert body["total_exams"] == 1
    assert [e["exam_id"] for e in body["exams"]] == [exam_a.id]


def test_instructor_analytics_reflects_pass_rate_and_risk(
    client, db, make_instructor, make_student, make_exam, auth_headers
):
    instructor = make_instructor()
    exam = make_exam(instructor=instructor, total_points=10, passing_score=50)
    student = make_student(course=exam.subject.course)
    student_headers = auth_headers(student.user)

    session_id = client.post(
        "/exam-sessions/start", headers=student_headers, json={"exam_id": exam.id}
    ).json()["id"]
    client.post(
        f"/exam-sessions/{session_id}/violations",
        headers=student_headers,
        data={"event_type": "TAB_SWITCH"},
    )
    submitted = client.put(f"/exam-sessions/submit/{session_id}", headers=student_headers)
    assert submitted.json()["passed"] is False  # 0/10, well under the 50% pass bar

    response = client.get("/analytics/instructor", headers=auth_headers(instructor.user))
    assert response.status_code == 200
    body = response.json()
    assert body["exams"][0]["submitted_count"] == 1
    assert body["exams"][0]["pass_rate"] == 0.0
    assert body["overall_average_risk_score"] == 15.0  # TAB_SWITCH weight, see risk_service.WEIGHTS


def test_school_analytics_aggregates_violation_breakdown(
    client, make_school, make_course, make_subject, make_instructor, make_user, make_student,
    make_exam, auth_headers
):
    school_a = make_school()
    admin_a = make_user("admin", school=school_a)
    instructor_a = make_instructor(user=make_user("instructor", school=school_a))
    course_a = make_course(school=school_a)
    exam = make_exam(instructor=instructor_a, subject=make_subject(course=course_a))
    student = make_student(course=course_a)
    student_headers = auth_headers(student.user)

    session_id = client.post(
        "/exam-sessions/start", headers=student_headers, json={"exam_id": exam.id}
    ).json()["id"]
    client.post(
        f"/exam-sessions/{session_id}/violations",
        headers=student_headers,
        data={"event_type": "COPY_PASTE"},
    )
    client.put(f"/exam-sessions/submit/{session_id}", headers=student_headers)

    response = client.get("/analytics/school", headers=auth_headers(admin_a))
    assert response.status_code == 200
    body = response.json()
    assert body["total_violations"] == 1
    assert body["violation_breakdown"] == {"COPY_PASTE": 1}
