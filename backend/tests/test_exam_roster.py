"""Exam roster management, including bulk-add.

**Bulk-add rosters the exam's CLASS, not its course.** It used to add every student in the
course, which was correct when a course was the widest thing an exam could be scoped to. Roster
inheritance made that wrong in two ways at once, and one click did both: it rosters people who are
not in this class, and because precedence is per-exam, the moment any explicit row exists the
section's own enrolment stops applying. An instructor with a healthy inherited class of three, in
a course of five, pressed "Add All" and silently ended up admitting five.

Scoped to the section it admits exactly who the exam already admitted, just explicitly - the
useful starting point for narrowing to a makeup or a deferred sitting. Adding somebody outside the
class is still possible one at a time, which is where a deliberate exception belongs.
"""
from app.services.academic_service import AcademicService


def test_bulk_add_rosters_the_sections_class(
    client, db, default_school, make_exam, make_student, auth_headers
):
    exam = make_exam()
    headers = auth_headers(exam.instructor.user)
    classmates = [make_student(course=exam.subject.course) for _ in range(3)]
    AcademicService.enroll(
        exam.section_id, [s.id for s in classmates], default_school.id, db
    )

    response = client.post(f"/exams/{exam.id}/roster/bulk-add", headers=headers)
    assert response.status_code == 200
    assert response.json()["added_count"] == 3

    roster = client.get(f"/exams/{exam.id}/roster", headers=headers).json()
    rostered_student_ids = {entry["student"]["id"] for entry in roster}
    assert rostered_student_ids == {s.id for s in classmates}


def test_bulk_add_does_not_widen_an_exam_beyond_its_class(
    client, db, default_school, make_exam, make_student, auth_headers
):
    """The defect this replaced. Same course, not in this section - one click used to admit them,
    and drop the inherited class in the same motion."""
    exam = make_exam()
    headers = auth_headers(exam.instructor.user)
    in_class = make_student(course=exam.subject.course)
    same_course_other_class = make_student(course=exam.subject.course)
    AcademicService.enroll(exam.section_id, [in_class.id], default_school.id, db)

    response = client.post(f"/exams/{exam.id}/roster/bulk-add", headers=headers)

    assert response.json()["added_count"] == 1
    roster = client.get(f"/exams/{exam.id}/roster", headers=headers).json()
    assert {entry["student"]["id"] for entry in roster} == {in_class.id}
    assert same_course_other_class.id not in {entry["student"]["id"] for entry in roster}


def test_bulk_add_skips_already_rostered_students(
    client, db, default_school, make_exam, make_student, auth_headers
):
    exam = make_exam()
    headers = auth_headers(exam.instructor.user)
    already_rostered = make_student(course=exam.subject.course, exam=exam)
    newly_available = make_student(course=exam.subject.course)
    AcademicService.enroll(
        exam.section_id, [already_rostered.id, newly_available.id], default_school.id, db
    )

    response = client.post(f"/exams/{exam.id}/roster/bulk-add", headers=headers)
    assert response.status_code == 200
    # Only the one not already on the roster should be newly added.
    assert response.json()["added_count"] == 1

    roster = client.get(f"/exams/{exam.id}/roster", headers=headers).json()
    rostered_student_ids = {entry["student"]["id"] for entry in roster}
    assert rostered_student_ids == {already_rostered.id, newly_available.id}


def test_bulk_add_on_an_empty_class_adds_nobody(
    client, make_exam, make_student, make_course, auth_headers
):
    """It must not fall back to the course when the class is empty - that is the lockout case, and
    quietly rostering the whole course would hide it rather than surface it."""
    exam = make_exam()
    headers = auth_headers(exam.instructor.user)
    make_student(course=exam.subject.course)

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
