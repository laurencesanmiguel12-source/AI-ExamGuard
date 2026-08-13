"""Load test for the two CPU-bound inference endpoints (face-check, object-check) a real exam
session polls every ~15s (see ExamRoom.jsx's setInterval(checkOnce, 5000/15000)). Built to answer a
concrete question from the live-readiness audit: has concurrent load ever been tested? (No - never,
confirmed by grepping for locust/k6/wrk/ab anywhere in the repo before this.)

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
    LOAD_TEST_TOKEN=$TOKEN LOAD_TEST_SESSION_IDS=39,40,41,...  # one id per --users, no sharing \
        ../.venv/Scripts/locust -f loadtest/locustfile.py \
        --host http://localhost:8000 --users 20 --spawn-rate 5 --run-time 2m --headless \
        --csv loadtest/results_20users
(Sweep --users across runs - e.g. 5, 15, 30, 50 - to find where latency stops being healthy.)
"""
import itertools
import os

from locust import HttpUser, between, task

SESSION_IDS = itertools.cycle(int(x) for x in os.environ["LOAD_TEST_SESSION_IDS"].split(","))
TOKEN = os.environ["LOAD_TEST_TOKEN"]
FRAME_PATH = os.path.join(os.path.dirname(__file__), "testframe.jpg")


class ExamPoller(HttpUser):
    # Jitter around the real ~15s object/face-check poll interval (ExamRoom.jsx), not a stress-only
    # tight loop - the question is "can it keep up with the REAL cadence at N concurrent students,"
    # not "what's the max raw throughput" (a different, less relevant question for this app).
    wait_time = between(13, 17)

    def on_start(self):
        self.session_id = next(SESSION_IDS)
        self.headers = {"Authorization": f"Bearer {TOKEN}"}
        with open(FRAME_PATH, "rb") as f:
            self.frame_bytes = f.read()

    @task
    def poll_face_and_object_check(self):
        files = {"file": ("frame.jpg", self.frame_bytes, "image/jpeg")}
        self.client.post(
            f"/exam-sessions/{self.session_id}/face-check",
            headers=self.headers, files=files, name="/face-check"
        )
        files = {"file": ("frame.jpg", self.frame_bytes, "image/jpeg")}
        self.client.post(
            f"/exam-sessions/{self.session_id}/object-check",
            headers=self.headers, files=files, name="/object-check"
        )
