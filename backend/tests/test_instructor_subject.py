"""Instructor-subject assignment: an admin assigns instructors to subjects.

**This no longer gates exam creation.** Until step 5 of the academic-hierarchy migration, an exam
named a subject and creation was gated on the caller being assigned to it - an approximation of
ownership that could not tell two instructors of the same subject apart, so each could reach the
other's work. An exam now names a SECTION, which names exactly one instructor, and that direct
check replaced the approximation. The tests below pin the replacement rather than the thing it
replaced.

instructor_subjects itself is still real and still admin-managed: it is the catalogue-level
statement of what an instructor teaches, and it is what the section form offers as choices.
"""
from datetime import datetime, timedelta, timezone


def _exam_payload(section_id):
    return {
        "title": "Midterm",
        "duration_minutes": 30,
        "passing_score": 50,
        "start_time": datetime.now(timezone.utc).isoformat(),
        "end_time": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
        "section_id": section_id,
    }


def test_subject_assignment_alone_does_not_let_an_instructor_reach_a_class(
    client, make_instructor, make_section, make_instructor_subject, auth_headers
):
    """The exact hole the section closed: both instructors are assigned to the subject, only one
    teaches this class, and assignment used to be the whole check."""
    section = make_section()
    intruder = make_instructor()
    subject = section.subject
    make_instructor_subject(intruder, subject)

    response = client.post(
        "/exams/", headers=auth_headers(intruder.user), json=_exam_payload(section.id)
    )

    assert response.status_code == 403


def test_the_instructor_who_teaches_the_section_can_create_its_exam(
    client, make_section, auth_headers
):
    section = make_section()

    response = client.post(
        "/exams/", headers=auth_headers(section.instructor.user), json=_exam_payload(section.id)
    )

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
