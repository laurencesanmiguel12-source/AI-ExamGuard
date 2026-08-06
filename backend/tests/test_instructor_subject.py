"""Instructor-subject assignment: admin assigns instructors to subjects, and exam creation/update
is gated on that assignment existing (see ExamService._require_subject_assignment)."""
from datetime import datetime, timedelta, timezone


def _exam_payload(subject_id):
    return {
        "title": "Midterm",
        "duration_minutes": 30,
        "passing_score": 50,
        "start_time": datetime.now(timezone.utc).isoformat(),
        "end_time": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
        "subject_id": subject_id,
        "instructor_id": 0,  # ignored server-side (see ExamService.create), but required by schema
    }


def test_unassigned_instructor_cannot_create_exam_for_subject(client, make_instructor, make_subject, auth_headers):
    instructor = make_instructor()
    subject = make_subject()

    response = client.post("/exams/", headers=auth_headers(instructor.user), json=_exam_payload(subject.id))

    assert response.status_code == 403


def test_assigned_instructor_can_create_exam_for_subject(
    client, make_instructor, make_subject, make_instructor_subject, auth_headers
):
    instructor = make_instructor()
    subject = make_subject()
    make_instructor_subject(instructor, subject)

    response = client.post("/exams/", headers=auth_headers(instructor.user), json=_exam_payload(subject.id))

    assert response.status_code == 200


def test_admin_can_assign_instructor_to_subject(client, make_instructor, make_subject, make_user, auth_headers):
    instructor = make_instructor()
    subject = make_subject()
    admin = make_user("admin")

    response = client.post(
        f"/instructors/{instructor.id}/subjects/",
        headers=auth_headers(admin),
        json={"subject_id": subject.id},
    )

    assert response.status_code == 200
    assert response.json()["subject_id"] == subject.id


def test_non_admin_cannot_assign_instructor_to_subject(client, make_instructor, make_subject, auth_headers):
    instructor = make_instructor()
    subject = make_subject()

    response = client.post(
        f"/instructors/{instructor.id}/subjects/",
        headers=auth_headers(instructor.user),
        json={"subject_id": subject.id},
    )

    assert response.status_code == 403


def test_admin_can_unassign_instructor_from_subject(
    client, make_instructor, make_subject, make_instructor_subject, make_user, auth_headers
):
    instructor = make_instructor()
    subject = make_subject()
    make_instructor_subject(instructor, subject)
    admin = make_user("admin")

    response = client.delete(f"/instructors/{instructor.id}/subjects/{subject.id}", headers=auth_headers(admin))
    assert response.status_code == 200

    # unassigned, so creating an exam for that subject is blocked again
    exam_response = client.post("/exams/", headers=auth_headers(instructor.user), json=_exam_payload(subject.id))
    assert exam_response.status_code == 403
