"""Near-miss capture: keeping the frames the phone detector nearly fired on.

The gap this closes: the training review queue can only show frames that produced a violation, so
an admin reviewing it only ever sees cases the model already got right. Measured on the 2026-09-04
batch - all three approved phone frames were already detected at 0.80-0.88, well clear of the 0.35
threshold, so that batch had almost no training value. The useful frames were being computed and
discarded.
"""
import os
from datetime import datetime, timezone

import pytest

from app.models.exam_session import ExamSession

from app.models.near_miss_capture import NearMissCapture
from app.services import object_detection_service as ods
from app.services import near_miss_capture_service as nmcs
from app.services.near_miss_capture_service import NearMissCaptureService

PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 64  # stand-in bytes; nothing here decodes an image


def _session(db, student, exam):
    """Built inline rather than as a fixture - conftest has no exam-session factory, and the
    other suites construct these the same way."""
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


@pytest.fixture(autouse=True)
def isolate_capture_side_effects(tmp_path, monkeypatch):
    """Capture writes a real JPEG next to the row it creates, and STORAGE_DIR resolves to the
    app's live evidence store. Without this the suite silently deposits image files into
    backend/storage/near_miss_evidence/ - 28 orphans on the first run, with no DB rows pointing at
    them, indistinguishable from real captured evidence.
    """
    monkeypatch.setattr(nmcs, "STORAGE_DIR", str(tmp_path / "near_miss_evidence"))
    ods._near_miss_counts.clear()
    yield
    ods._near_miss_counts.clear()


def _capture(db, session, conf, image=PNG):
    return NearMissCaptureService.capture(
        session_id=session.id, detector="PHONE", confidence=conf, image_bytes=image, db=db
    )


def test_captures_a_frame_just_below_the_firing_threshold(db, make_student, make_exam):
    session = _session(db, make_student(), make_exam())

    capture = _capture(db, session, 0.31)

    assert capture is not None
    assert capture.training_review_status == "PENDING"
    assert capture.confidence == pytest.approx(0.31)
    assert os.path.exists(capture.evidence_path)


def test_ignores_frames_the_model_saw_nothing_in(db, make_student, make_exam):
    """Below the candidate floor the detector found essentially nothing, and keeping those would
    just be retaining webcam frames of students doing nothing wrong."""
    session = _session(db, make_student(), make_exam())

    assert _capture(db, session, 0.05) is None
    assert db.query(NearMissCapture).count() == 0


def test_stops_after_the_per_session_cap(db, make_student, make_exam):
    """A two-hour exam polls ~480 times. Without a cap, one student sitting near the boundary
    could have hundreds of frames retained despite never being flagged."""
    session = _session(db, make_student(), make_exam())

    for _ in range(ods.NEAR_MISS_MAX_PER_SESSION + 5):
        _capture(db, session, 0.30)

    assert db.query(NearMissCapture).count() == ods.NEAR_MISS_MAX_PER_SESSION


def test_the_cap_resets_when_the_session_ends(db, make_student, make_exam):
    session = _session(db, make_student(), make_exam())
    for _ in range(ods.NEAR_MISS_MAX_PER_SESSION):
        _capture(db, session, 0.30)

    ods.discard_session(session.id)

    assert _capture(db, session, 0.30) is not None


def test_a_capture_failure_never_breaks_the_detection_poll(db, make_student, make_exam):
    """This runs on the hot proctoring path. A failure here should cost one training sample, not
    a student's exam."""
    session = _session(db, make_student(), make_exam())

    assert _capture(db, session, 0.30, image=None) is None
    # And the session is still usable afterwards - no poisoned transaction left behind.
    assert _capture(db, session, 0.30) is not None


def test_queue_puts_the_closest_calls_first(db, make_student, make_exam):
    session = _session(db, make_student(), make_exam())
    for conf in (0.22, 0.34, 0.27):
        _capture(db, session, conf)

    pending = NearMissCaptureService.list_pending(db, school_id=None)

    assert [round(c.confidence, 2) for c in pending] == [0.34, 0.27, 0.22]


def test_reviewing_records_the_decision(db, make_user, make_student, make_exam):
    admin = make_user("admin")
    capture = _capture(db, _session(db, make_student(), make_exam()), 0.30)

    NearMissCaptureService.review(capture.id, "APPROVED", admin.id, db, school_id=None)

    db.refresh(capture)
    assert capture.training_review_status == "APPROVED"
    assert NearMissCaptureService.list_pending(db, school_id=None) == []


def test_a_capture_cannot_be_reviewed_twice(db, make_user, make_student, make_exam):
    admin = make_user("admin")
    capture = _capture(db, _session(db, make_student(), make_exam()), 0.30)
    NearMissCaptureService.review(capture.id, "REJECTED", admin.id, db, school_id=None)

    with pytest.raises(Exception):
        NearMissCaptureService.review(capture.id, "APPROVED", admin.id, db, school_id=None)


def test_an_admin_cannot_see_another_schools_captures(
    db, make_user, make_school, make_course, make_subject, make_exam, make_student
):
    other_school = make_school()
    other_exam = make_exam(subject=make_subject(course=make_course(school=other_school)))
    _capture(db, _session(db, make_student(), other_exam), 0.30)

    own_admin = make_user("admin")

    assert NearMissCaptureService.list_pending(db, school_id=own_admin.school_id) == []
