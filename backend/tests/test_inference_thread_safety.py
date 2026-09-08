"""The inference routes run their blocking CPU work in a threadpool, which is only safe because
the detector/model objects underneath are per-thread. This is the check that the per-thread part
still holds: run the real detectors concurrently and assert nobody raises.

Before the fix (a single shared module-level cv2.FaceDetectorYN), this reproduced as
`cv2.error: (-215:Assertion failed) buf.shape() == m.shape()` - it does not need many iterations
to show up, and it surfaced as real 500s in a load test, not a theoretical race.
"""
import threading

import numpy as np

from app.services import face_service, object_detection_service

THREADS = 4
ITERATIONS = 15


def _hammer(target, errors):
    try:
        for _ in range(ITERATIONS):
            target()
    except Exception as exc:  # noqa: BLE001 - any exception at all is the failure signal
        errors.append(exc)


def _run_concurrently(target):
    errors = []
    threads = [threading.Thread(target=_hammer, args=(target, errors)) for _ in range(THREADS)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    return errors


def test_yunet_detector_survives_concurrent_detection():
    # Two DIFFERENT frame sizes, alternating, because the corruption comes from setInputSize()
    # mutating the shared detector between another thread's setInputSize() and its detect().
    frames = [
        np.zeros((480, 640, 3), dtype=np.uint8),
        np.zeros((720, 1280, 3), dtype=np.uint8),
    ]
    counter = threading.local()

    def detect_once():
        counter.i = getattr(counter, "i", 0) + 1
        face_service._detect_largest_face(frames[counter.i % len(frames)])

    assert _run_concurrently(detect_once) == []


def test_each_thread_gets_its_own_models():
    seen = []
    lock = threading.Lock()

    def record_ids():
        ids = (
            id(object_detection_service.base_model()),
            id(object_detection_service.phone_model()),
            id(object_detection_service.pose_model()),
            id(face_service._detector()),
        )
        with lock:
            seen.append(ids)

    threads = [threading.Thread(target=record_ids) for _ in range(THREADS)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(seen) == THREADS
    # No object may be shared across two threads - that sharing is exactly the bug.
    assert len(set(seen)) == THREADS
    for position in range(4):
        instances = [ids[position] for ids in seen]
        assert len(set(instances)) == THREADS

    # ...and a thread must reuse its own, or every request would rebuild the models.
    assert object_detection_service.base_model() is object_detection_service.base_model()
    assert face_service._detector() is face_service._detector()
