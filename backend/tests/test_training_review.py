"""Continuous-training review queue: PHONE_DETECTED/MULTIPLE_PEOPLE evidence auto-enters a
PENDING review queue, only an admin can approve/reject it, and RetentionService's 90-day purge
must never delete evidence still awaiting review or an approved-but-not-yet-exported sample -
otherwise a training candidate could vanish before a human ever saw it. Identity-linked evidence
(FACE_LOST) must never enter the queue at all - see TRAINING_CANDIDATE_EVENT_TYPES."""
from datetime import datetime, timedelta, timezone

from app.models.violation import Violation
from app.services.retention_service import RetentionService


def _log_violation(client, headers, session_id, event_type):
    response = client.post(
        f"/exam-sessions/{session_id}/violations",
        headers=headers,
        data={"event_type": event_type},
        files={"evidence": ("evidence.jpg", b"fake jpeg bytes", "image/jpeg")},
    )
    assert response.status_code == 200
    return response.json()


def test_phone_detected_evidence_auto_enters_review_queue(client, make_student, make_exam, auth_headers, db):
    exam = make_exam(total_points=0, passing_score=50)
    student = make_student(course=exam.subject.course)
    headers = auth_headers(student.user)
    start = client.post("/exam-sessions/start", headers=headers, json={"exam_id": exam.id})
    session_id = start.json()["id"]

    v = _log_violation(client, headers, session_id, "PHONE_DETECTED")

    row = db.query(Violation).filter(Violation.id == v["id"]).first()
    assert row.training_review_status == "PENDING"


def test_face_lost_evidence_never_enters_review_queue(client, make_student, make_exam, auth_headers, db):
    """FACE_LOST evidence is a biometric-identity frame, not object-detection evidence - it must
    stay out of the training pipeline entirely until there's separate consent for that."""
    exam = make_exam(total_points=0, passing_score=50)
    student = make_student(course=exam.subject.course)
    headers = auth_headers(student.user)
    start = client.post("/exam-sessions/start", headers=headers, json={"exam_id": exam.id})
    session_id = start.json()["id"]

    v = _log_violation(client, headers, session_id, "FACE_LOST")

    row = db.query(Violation).filter(Violation.id == v["id"]).first()
    assert row.training_review_status is None


def test_admin_can_approve_a_pending_candidate(client, make_student, make_exam, auth_headers, make_user, db):
    exam = make_exam(total_points=0, passing_score=50)
    student = make_student(course=exam.subject.course)
    admin = make_user("admin", school=exam.subject.course.school)
    headers = auth_headers(student.user)
    start = client.post("/exam-sessions/start", headers=headers, json={"exam_id": exam.id})
    session_id = start.json()["id"]
    v = _log_violation(client, headers, session_id, "MULTIPLE_PEOPLE")

    pending = client.get("/admin/training-review/pending", headers=auth_headers(admin))
    assert pending.status_code == 200
    assert any(c["id"] == v["id"] for c in pending.json())

    review = client.put(
        f"/admin/training-review/{v['id']}",
        headers=auth_headers(admin),
        json={"decision": "APPROVED"},
    )
    assert review.status_code == 200

    row = db.query(Violation).filter(Violation.id == v["id"]).first()
    assert row.training_review_status == "APPROVED"
    assert row.training_reviewed_by == admin.id


def test_non_admin_cannot_review_training_candidates(client, make_instructor, make_student, make_exam, auth_headers):
    instructor = make_instructor()
    exam = make_exam(instructor=instructor, total_points=0, passing_score=50)
    student = make_student(course=exam.subject.course)
    student_headers = auth_headers(student.user)
    start = client.post("/exam-sessions/start", headers=student_headers, json={"exam_id": exam.id})
    session_id = start.json()["id"]
    v = _log_violation(client, student_headers, session_id, "PHONE_DETECTED")

    response = client.put(
        f"/admin/training-review/{v['id']}",
        headers=auth_headers(instructor.user),
        json={"decision": "APPROVED"},
    )
    assert response.status_code == 403


def test_purge_skips_pending_review_and_unexported_approved_evidence(db, make_student, make_exam, make_user):
    exam = make_exam(total_points=0, passing_score=50)
    student = make_student(course=exam.subject.course)
    school_id = student.user.school_id
    admin = make_user("admin", school=exam.subject.course.school)

    old = datetime.now(timezone.utc) - timedelta(days=100)

    from app.models.exam_session import ExamSession
    session = ExamSession(
        exam_id=exam.id, student_id=student.id, status="SUBMITTED",
        started_at=datetime.now(timezone.utc),
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    pending = Violation(
        exam_session_id=session.id, event_type="PHONE_DETECTED",
        evidence_path="/tmp/does-not-need-to-exist-pending.jpg",
        training_review_status="PENDING", created_at=old,
    )
    approved_unexported = Violation(
        exam_session_id=session.id, event_type="PHONE_DETECTED",
        evidence_path="/tmp/does-not-need-to-exist-approved.jpg",
        training_review_status="APPROVED", created_at=old,
    )
    rejected = Violation(
        exam_session_id=session.id, event_type="PHONE_DETECTED",
        evidence_path="/tmp/does-not-need-to-exist-rejected.jpg",
        training_review_status="REJECTED", created_at=old,
    )
    db.add_all([pending, approved_unexported, rejected])
    db.commit()
    db.refresh(pending)
    db.refresh(approved_unexported)
    db.refresh(rejected)

    purged = RetentionService.purge_expired_evidence(db, admin.id, school_id)

    db.refresh(pending)
    db.refresh(approved_unexported)
    db.refresh(rejected)

    assert purged == 1  # only the REJECTED one
    assert pending.evidence_path is not None
    assert approved_unexported.evidence_path is not None
    assert rejected.evidence_path is None
