"""Regression tests for the passing_score / max_risk_score percentage bounds.

Both fields are percentages (0-100), not point totals. `passing_score` is compared against
`score / total_points * 100` in exam_session_service, and `max_risk_score` against a risk score
that RiskService caps at 100. Neither was bounded at the API before, and both fail SILENTLY when
out of range rather than erroring:

- passing_score above 100 makes an exam unpassable; below 0 passes everybody.
- max_risk_score above 100 can never be exceeded, so retake-flagging is off with no indication.

The UI hint for passing_score used to say it was a point total (fixed in 753a400), so
points-style values genuinely were entered under the old reading - on a 50-point exam, "30"
meant 30 points to the instructor and 30% (15 points) to the scorer. These tests pin the bound
that stops the next one being accepted.
"""
from datetime import datetime, timedelta, timezone


def _exam_payload(subject, instructor, **overrides):
    payload = {
        "title": "Bounds Test",
        "duration_minutes": 30,
        "total_points": 50,
        "passing_score": 60,
        "start_time": datetime.now(timezone.utc).isoformat(),
        "end_time": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
        "subject_id": subject.id,
        "instructor_id": instructor.id,
    }
    payload.update(overrides)
    return payload


def test_passing_score_above_100_is_rejected(
    client, make_instructor, make_subject, make_instructor_subject, auth_headers
):
    """150 is the shape of a points-style value on a 150-point exam - it would silently make the
    exam unpassable, since a percentage can never exceed 100."""
    instructor = make_instructor()
    subject = make_subject()
    make_instructor_subject(instructor, subject)

    response = client.post(
        "/exams/",
        headers=auth_headers(instructor.user),
        json=_exam_payload(subject, instructor, passing_score=150),
    )

    assert response.status_code == 422


def test_negative_passing_score_is_rejected(
    client, make_instructor, make_subject, make_instructor_subject, auth_headers
):
    instructor = make_instructor()
    subject = make_subject()
    make_instructor_subject(instructor, subject)

    response = client.post(
        "/exams/",
        headers=auth_headers(instructor.user),
        json=_exam_payload(subject, instructor, passing_score=-1),
    )

    assert response.status_code == 422


def test_max_risk_score_above_100_is_rejected(
    client, make_instructor, make_subject, make_instructor_subject, auth_headers
):
    """RiskService caps the score at 100, so a threshold above it can never be crossed - retake
    flagging would be silently disabled rather than misconfigured loudly."""
    instructor = make_instructor()
    subject = make_subject()
    make_instructor_subject(instructor, subject)

    response = client.post(
        "/exams/",
        headers=auth_headers(instructor.user),
        json=_exam_payload(subject, instructor, max_risk_score=101),
    )

    assert response.status_code == 422


def test_the_bounds_are_inclusive(
    client, make_instructor, make_subject, make_instructor_subject, auth_headers
):
    """0 and 100 are both legitimate: pass-everybody and perfect-score-required respectively."""
    instructor = make_instructor()
    subject = make_subject()
    make_instructor_subject(instructor, subject)

    for value in (0, 100):
        response = client.post(
            "/exams/",
            headers=auth_headers(instructor.user),
            json=_exam_payload(subject, instructor, passing_score=value, max_risk_score=value),
        )
        assert response.status_code == 200, response.text


def test_an_update_cannot_push_passing_score_out_of_range(
    client, make_instructor, make_subject, make_instructor_subject, make_exam, auth_headers
):
    """ExamUpdate is a separate schema - bounding only ExamCreate would leave the same hole open
    one PUT away."""
    instructor = make_instructor()
    subject = make_subject()
    make_instructor_subject(instructor, subject)
    exam = make_exam(instructor=instructor, total_points=50, passing_score=60)

    response = client.put(
        f"/exams/{exam.id}",
        headers=auth_headers(instructor.user),
        json={"passing_score": 150},
    )

    assert response.status_code == 422
