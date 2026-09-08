"""Load test for the two CPU-bound inference endpoints (face-check, object-check) a real exam
session polls. Built to answer a concrete question from the live-readiness audit: has concurrent
load ever been tested? (No - never, confirmed by grepping for locust/k6/wrk/ab anywhere in the repo
before this.)

Mirrors ExamRoom.jsx's real poll loop, which changed 2026-09-07 from one frame every 5s to
CAPTURE_INTERVAL_MS = 1000 (1 fps). Two things about that loop matter for load and are modelled
below rather than approximated:

  * Pacing, not sleeping. The frontend drives checkOnce from setInterval and guards it with an
    `inFlight` flag, so a poll that overruns the interval doesn't stack a second one - the next
    tick is skipped and the effective rate degrades to whatever the backend can serve.
    constant_pacing(1) is the exact same behavior (start a task every 1s; if the last overran,
    start the next immediately), which `between()` is not - `between(0.9, 1.1)` would add its wait
    ON TOP of a slow response and silently under-load the server exactly when it's struggling,
    hiding the thing this test exists to find.
  * Only 1 poll in AUDIT_EVERY_N_POLLS (15 at 1 fps) sends a full frame to face-check. The other
    14 send a ~7KB client-cropped face with client_confident_crop=true, which FaceService.verify
    short-circuits: no YuNet, no pose-model fallback, no LBPH predict. Sending full frames on
    every poll (what this file did when the cadence was 15s and the client-crop path didn't exist)
    would overstate face-check cost by ~15x at this rate and make the result meaningless.
    object-check has no such path - every poll sends the full frame.

Payloads are real, not synthetic. testframe720.jpg is a real OEP webcam frame containing a real
face, upscaled to the 1280x720 useCamera.js actually requests and re-encoded at the 0.92 quality
canvas.toBlob defaults to; testcrop.jpg is the 200x200 grayscale q0.90 crop
useClientFaceDetector.js produces from it. The previous testframe.jpg was synthetic noise with no
face in it, which is not a neutral simplification: with no face to find, YuNet fails and every
single face-check falls through to the expensive pose-model fallback, a path a real frame with a
visible face never touches. Regenerate both with loadtest/make_payloads.py.

The student5 face model must be enrolled from the SAME subject as testframe720.jpg (make_payloads.py
prints the reminder) - otherwise every audit poll logs an IDENTITY_MISMATCH violation plus an
evidence-file write, adding DB and disk load per poll that a legitimate exam session never
generates.

Known remaining artifact: replaying ONE frame forever is exactly what _check_static_image exists to
catch, so a run still logs some STATIC_IMAGE_SUSPECTED violations (with evidence writes) that a
live webcam wouldn't. Measured at ~1.7 per simulated user per 90s run - small next to the inference
cost, and erring toward pessimism, so it's left alone rather than fixed with a frame rotation that
would make the per-request inference cost vary run to run. Clean up the rows and their
storage/violation_evidence files after a run.

Dev-only tool, deliberately NOT in backend/requirements.txt (would ship into the production Docker
image otherwise, same reasoning backend/.dockerignore already excludes training/) - `pip install
locust` separately before running this.

Each simulated user gets its OWN exam_sessions row (LOAD_TEST_SESSION_IDS, comma-separated pool,
one consumed per spawned user) rather than sharing one - tried sharing one first and found it's a
real confound, not a simplification: face_service.py's verify() reads/writes/commits the SAME
ExamSession row every call (head_down tracking), so N users sharing one session_id serializes on a
real Postgres row lock, which would swamp and hide whatever the actual event-loop/CPU-inference
answer is. All sessions still belong to the same real student (student5) reusing one token/auth
check - only the row-per-request identity matters for isolating this question, not N distinct
students/face-enrollments.

Authenticates ONCE via LOAD_TEST_TOKEN (fetched before starting locust, see Usage below) rather
than each simulated user calling /auth/login in on_start - real students log in once well before
polling starts, not simultaneously with every poll cycle. Also sidesteps a real interaction found
while building this: every simulated user here shares one IP (this test machine), so N users all
logging in at once would trip the /auth/login rate limit (10/minute, see app/core/rate_limit.py) -
a genuine artifact of single-machine testing, not something N real students on N real devices
would hit, and not what this test is trying to measure.

Usage (from backend/, against a server started the SAME way production is - no --reload, no
--workers override, matching Dockerfile's CMD):
    ../.venv/Scripts/python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000
    TOKEN=$(curl -s -X POST http://localhost:8000/auth/login -H "Content-Type: application/json" \
        -d '{"email":"student5@example.com","password":"TestPass123!"}' | python -c \
        "import sys,json; print(json.load(sys.stdin)['access_token'])")
    LOAD_TEST_TOKEN=$TOKEN LOAD_TEST_SESSION_IDS=104,105,106,...  # one id per --users, no sharing \
        ../.venv/Scripts/locust -f loadtest/locustfile.py \
        --host http://localhost:8000 --users 20 --spawn-rate 5 --run-time 2m --headless \
        --csv loadtest/results_20users
(Sweep --users across runs - e.g. 5, 10, 20, 50 - to find where latency stops being healthy.)
"""
import itertools
import os

from locust import HttpUser, constant_pacing, task

SESSION_IDS = itertools.cycle(int(x) for x in os.environ["LOAD_TEST_SESSION_IDS"].split(","))
TOKEN = os.environ["LOAD_TEST_TOKEN"]
FRAME_PATH = os.path.join(os.path.dirname(__file__), "testframe720.jpg")
CROP_PATH = os.path.join(os.path.dirname(__file__), "testcrop.jpg")

# Mirrors ExamRoom.jsx: capture interval is the knob, and the audit poll is DERIVED from it to
# hold the ~15s server-side audit cadence the head-down constants were tuned against - exactly as
# AUDIT_EVERY_N_POLLS does there. Overridable so a sweep can re-measure the old 5s cadence with
# identical payloads instead of comparing against a differently-built older run.
CAPTURE_INTERVAL_SECONDS = float(os.environ.get("LOAD_TEST_CAPTURE_INTERVAL", "1.0"))
AUDIT_EVERY_N_POLLS = max(1, round(15.0 / CAPTURE_INTERVAL_SECONDS))


class ExamPoller(HttpUser):
    # See the module docstring: this is pacing, not a wait, so a slow backend does NOT get a
    # correspondingly lighter offered load - which is the whole point of the measurement.
    wait_time = constant_pacing(CAPTURE_INTERVAL_SECONDS)

    def on_start(self):
        self.session_id = next(SESSION_IDS)
        self.headers = {"Authorization": f"Bearer {TOKEN}"}
        self.poll_count = 0
        with open(FRAME_PATH, "rb") as f:
            self.frame_bytes = f.read()
        with open(CROP_PATH, "rb") as f:
            self.crop_bytes = f.read()

    @task
    def poll_face_and_object_check(self):
        self.poll_count += 1
        is_audit_poll = self.poll_count % AUDIT_EVERY_N_POLLS == 0

        # Reported as two separate names so the cheap client-crop path and the expensive full
        # server-side audit don't get averaged into one meaningless middle number.
        if is_audit_poll:
            payload = {"file": ("frame.jpg", self.frame_bytes, "image/jpeg")}
            data, name = {}, "/face-check (audit, full frame)"
        else:
            payload = {"file": ("crop.jpg", self.crop_bytes, "image/jpeg")}
            data, name = {"client_confident_crop": "true"}, "/face-check (client crop)"
        self.client.post(
            f"/exam-sessions/{self.session_id}/face-check",
            headers=self.headers, files=payload, data=data, name=name
        )

        files = {"file": ("frame.jpg", self.frame_bytes, "image/jpeg")}
        self.client.post(
            f"/exam-sessions/{self.session_id}/object-check",
            headers=self.headers, files=files, name="/object-check"
        )
