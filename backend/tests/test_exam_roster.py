"""Exam roster management, including the bulk-add endpoint added to close a real reported gap:
since 7c21c35 removed the course-wide-by-default fallback, a newly self-registered student is
invisible to an exam's roster (and so can't see/take the exam) until an instructor adds them one
at a time via the "Add Students" list - bulk-add lets them add every currently-available student
in one action instead."""


def test_bulk_add_rosters_every_available_student(client, make_exam, make_student, auth_headers):
    exam = make_exam()
    headers = auth_headers(exam.instructor.user)
    students = [make_student(course=exam.subject.course) for _ in range(3)]

    response = client.post(f"/exams/{exam.id}/roster/bulk-add", headers=headers)
    assert response.status_code == 200
    assert response.json()["added_count"] == 3

    roster = client.get(f"/exams/{exam.id}/roster", headers=headers).json()
    rostered_student_ids = {entry["student"]["id"] for entry in roster}
    assert rostered_student_ids == {s.id for s in students}


def test_bulk_add_skips_already_rostered_students(client, make_exam, make_student, auth_headers):
    exam = make_exam()
    headers = auth_headers(exam.instructor.user)
    already_rostered = make_student(course=exam.subject.course, exam=exam)
    newly_available = make_student(course=exam.subject.course)

    response = client.post(f"/exams/{exam.id}/roster/bulk-add", headers=headers)
    assert response.status_code == 200
    # Only the one not already on the roster should be newly added.
    assert response.json()["added_count"] == 1

    roster = client.get(f"/exams/{exam.id}/roster", headers=headers).json()
    rostered_student_ids = {entry["student"]["id"] for entry in roster}
    assert rostered_student_ids == {already_rostered.id, newly_available.id}


def test_bulk_add_never_rosters_a_different_courses_student(
    client, make_exam, make_student, make_course, auth_headers
):
    exam = make_exam()
    headers = auth_headers(exam.instructor.user)
    other_course_student = make_student(course=make_course())

    response = client.post(f"/exams/{exam.id}/roster/bulk-add", headers=headers)
    assert response.status_code == 200
    assert response.json()["added_count"] == 0

    roster = client.get(f"/exams/{exam.id}/roster", headers=headers).json()
    assert roster == []


def test_admin_can_list_a_roster_in_their_own_school(client, make_exam, make_student, make_user, auth_headers):
    """require_exam_owner's admin branch referenced Subject without importing it, so EVERY route
    behind it (roster, exam content, reports, exam update/delete) raised NameError -> 500 for any
    admin or super admin. Live symptom: the roster page just failed to load, so an admin could not
    see or add any student. The instructor branch never touched Subject, which is why the existing
    instructor-only tests all passed while the admin path was completely broken."""
    exam = make_exam()
    student = make_student(course=exam.subject.course, exam=exam)

    response = client.get(f"/exams/{exam.id}/roster", headers=auth_headers(make_user("admin")))

    assert response.status_code == 200
    assert [entry["student"]["id"] for entry in response.json()] == [student.id]


def test_non_owner_instructor_cannot_bulk_add(client, make_exam, make_instructor, make_student, auth_headers):
    owner = make_instructor()
    attacker = make_instructor()
    exam = make_exam(instructor=owner)
    make_student(course=exam.subject.course)

    response = client.post(f"/exams/{exam.id}/roster/bulk-add", headers=auth_headers(attacker.user))
    assert response.status_code == 403
