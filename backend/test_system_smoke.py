"""End-to-end system smoke test: walks the real admin -> instructor -> student flow through
FastAPI's TestClient - school signup, catalog setup, exam authoring, a full proctored attempt
(answer, violation, submit), then checks the resulting numbers show up correctly in the exam
report and the /analytics endpoints. One narrative script covering the whole system in the order
a real deployment would actually use it, rather than the isolated per-route pytest suite in tests/.

Runs against the isolated `ai_examguard_test` database with the same schema-once /
transaction-rolled-back-after isolation tests/conftest.py uses - safe to re-run any time, never
touches the real dev database, and needs no server already running (TestClient drives the app
in-process).

Deliberately placed at backend/ root, not inside tests/ - pytest.ini's `testpaths = tests` means
CI's `pytest` run never picks this up (see backend/test_violation_extension.py for the same
placement convention already used for a hand-run check). Run directly:

    cd backend && ../.venv/Scripts/python.exe test_system_smoke.py
"""
import os
import re
from datetime import datetime, timedelta, timezone

os.environ["ALLOWED_ORIGINS"] = "http://localhost:5173"

_env_path = os.path.join(os.path.dirname(__file__), ".env")
with open(_env_path) as f:
    for line in f:
        if line.startswith("DATABASE_URL="):
            _dev_url = line.strip().split("=", 1)[1]
            os.environ["DATABASE_URL"] = re.sub(r"/[^/]+$", "/ai_examguard_test", _dev_url)
            break
    else:
        raise RuntimeError(f"No DATABASE_URL line found in {_env_path}")

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

import app.models  # noqa: E402, F401 - registers every model on Base.metadata before create_all
from app.core.database import get_db  # noqa: E402
from app.main import app as fastapi_app  # noqa: E402
from app.models.base import Base  # noqa: E402
from app.models.role import Role  # noqa: E402

engine = create_engine(os.environ["DATABASE_URL"])
Base.metadata.create_all(engine)
connection = engine.connect()
transaction = connection.begin()
db = sessionmaker(bind=connection)()


def _override_get_db():
    yield db


# Base.metadata.create_all only builds the schema - it skips the data migration that seeds
# admin/instructor/student Role rows in a real deployment (Alembic migration, not part of the
# ORM-level table definitions). tests/conftest.py's make_role fixture papers over this per-test;
# this script isn't pytest, so seed the same three rows once, up front.
for role_name in ("admin", "instructor", "student"):
    if db.query(Role).filter(Role.name == role_name).first() is None:
        db.add(Role(name=role_name))
db.commit()


fastapi_app.dependency_overrides[get_db] = _override_get_db
client = TestClient(fastapi_app)

PASSWORD = "TestPass123!"
_failures = []


def check(label, condition):
    print(f"[{'OK' if condition else 'FAIL'}] {label}")
    if not condition:
        _failures.append(label)


def auth(email):
    r = client.post("/auth/login", json={"email": email, "password": PASSWORD})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


print("=== 1. School signup (the only way an admin account gets created) ===")
school = client.post("/schools/register", json={
    "code": "SMOKE", "name": "Smoke Test University", "slug": "smoke-test-university",
    "email": "smoke_admin@example.com", "password": PASSWORD,
    "first_name": "Smoke", "last_name": "Admin",
})
check("school registered", school.status_code == 200)
admin_headers = auth("smoke_admin@example.com")

print("\n=== 2. Admin builds the catalog ===")
course = client.post("/courses/", headers=admin_headers, json={"code": "BSCS", "name": "BS Computer Science"})
check("course created", course.status_code == 200)
course_id = course.json()["id"]

subject = client.post("/subjects/", headers=admin_headers, json={
    "code": "CS101", "name": "Intro to CS", "course_id": course_id,
})
check("subject created", subject.status_code == 200)
subject_id = subject.json()["id"]

instructor = client.post("/instructors/", headers=admin_headers, json={
    "employee_number": "EMP-SMOKE-01", 
    "email": "smoke_instructor@example.com", "password": PASSWORD,
    "first_name": "Smoke", "last_name": "Instructor",
})
check("instructor created", instructor.status_code == 200)
instructor_id = instructor.json()["id"]
instructor_headers = auth("smoke_instructor@example.com")

assignment = client.post(f"/instructors/{instructor_id}/subjects/", headers=admin_headers, json={
    "subject_id": subject_id,
})
check("instructor assigned to subject", assignment.status_code == 200)

print("\n=== 3. Instructor authors an exam ===")
now = datetime.now(timezone.utc)
exam = client.post("/exams/", headers=instructor_headers, json={
    "title": "Smoke Test Exam", "duration_minutes": 30, "total_points": 10, "passing_score": 50,
    "start_time": (now - timedelta(hours=1)).isoformat(), "end_time": (now + timedelta(hours=1)).isoformat(),
    "is_active": True, "subject_id": subject_id, "instructor_id": instructor_id,
})
check("exam created", exam.status_code == 200)
exam_id = exam.json()["id"]

question = client.post(f"/exams/{exam_id}/questions", headers=instructor_headers, json={
    "question_text": "2 + 2 = ?", "question_type": "MULTIPLE_CHOICE", "points": 10, "order_number": 1,
})
check("question created", question.status_code == 200)
question_id = question.json()["id"]

correct = client.post(f"/exams/{exam_id}/questions/{question_id}/choices", headers=instructor_headers, json={
    "choice_text": "4", "is_correct": True,
})
client.post(f"/exams/{exam_id}/questions/{question_id}/choices", headers=instructor_headers, json={
    "choice_text": "5", "is_correct": False,
})
check("choices created", correct.status_code == 200)
correct_choice_id = correct.json()["id"]

print("\n=== 4. Admin provisions a student (accommodated - skips face check for this smoke run) ===")
student = client.post("/students/", headers=admin_headers, json={
    "course_id": course_id, "email": "smoke_student@example.com",
    "password": PASSWORD, "first_name": "Smoke", "last_name": "Student",
})
check("student created", student.status_code == 200)
student_id = student.json()["id"]
update = client.put(f"/students/{student_id}", headers=admin_headers, json={"skip_face_check": True})
check("student accommodated (skip_face_check)", update.status_code == 200 and update.json()["skip_face_check"] is True)
student_headers = auth("smoke_student@example.com")

print("\n=== 4b. Instructor rosters the student for this exam ===")
# Required since the 2026-08-20 policy flip (ExamService.is_student_eligible): an exam with zero
# roster rows is no longer course-wide, so a student can't start it until explicitly rostered.
# This script predated that flip and failed at "session started" with 403 "This exam is not
# available for your course." until this step was added.
roster_add = client.post(f"/exams/{exam_id}/roster/bulk-add", headers=instructor_headers)
check("student rostered (bulk-add)", roster_add.status_code == 200 and roster_add.json()["added_count"] == 1)

# Admin reads the same roster: require_exam_owner's admin branch used Subject without importing
# it, so this 500'd for every admin/super_admin while the instructor path above worked fine.
admin_roster = client.get(f"/exams/{exam_id}/roster", headers=admin_headers)
check(
    "admin can read the roster (not a 500)",
    admin_roster.status_code == 200 and len(admin_roster.json()) == 1,
)

print("\n=== 5. Student takes the exam: start -> answer -> violation -> submit ===")
session = client.post("/exam-sessions/start", headers=student_headers, json={"exam_id": exam_id})
check("session started", session.status_code == 200)
session_id = session.json()["id"]

answer = client.post(f"/exam-sessions/{session_id}/answers", headers=student_headers, json={
    "question_id": question_id, "choice_id": correct_choice_id,
})
check("answer scored correct", answer.status_code == 200 and answer.json()["is_correct"] is True)

violation = client.post(
    f"/exam-sessions/{session_id}/violations", headers=student_headers,
    data={"event_type": "TAB_SWITCH"},
)
check("violation logged", violation.status_code == 200)

submitted = client.put(f"/exam-sessions/submit/{session_id}", headers=student_headers)
check("exam submitted", submitted.status_code == 200)
result = submitted.json()
check("scored 10/10 and passed", result["score"] == 10 and result["percentage"] == 100.0 and result["passed"] is True)

print("\n=== 6. Reporting reflects the attempt ===")
report = client.get(f"/exams/{exam_id}/report", headers=instructor_headers).json()
check("report counts the submission", report["submitted_count"] == 1 and report["pass_count"] == 1)
check("report's violation_breakdown counts the TAB_SWITCH", report["violation_breakdown"] == {"TAB_SWITCH": 1})
check("report's average_risk_score reflects TAB_SWITCH's weight (15)", report["average_risk_score"] == 15.0)

print("\n=== 7. New /analytics endpoints reflect the same attempt ===")
instructor_analytics = client.get("/analytics/instructor", headers=instructor_headers).json()
check("instructor analytics shows the one exam", instructor_analytics["total_exams"] == 1)
check("instructor analytics overall_pass_rate is 100%", instructor_analytics["overall_pass_rate"] == 100.0)

school_analytics = client.get("/analytics/school", headers=admin_headers).json()
check("school analytics shows the one exam", school_analytics["total_exams"] == 1)
check("school analytics attributes it to the right instructor", (
    len(school_analytics["instructors"]) == 1
    and school_analytics["instructors"][0]["instructor_id"] == instructor_id
    and school_analytics["instructors"][0]["exam_count"] == 1
))

print("\n=== 8. Spot-check a few other core routes stay healthy ===")
check("admin audit-log reachable", client.get("/admin/audit-log", headers=admin_headers).status_code == 200)
check("student results list reachable", client.get("/exam-sessions", headers=student_headers).status_code == 200)
check("instructor live-monitor reachable", client.get("/exam-sessions/live", headers=instructor_headers).status_code == 200)

db.close()
transaction.rollback()
connection.close()

print("\n" + "=" * 60)
if _failures:
    print(f"{len(_failures)} CHECK(S) FAILED:")
    for f in _failures:
        print(f"  - {f}")
    raise SystemExit(1)
print("All checks passed - full admin -> instructor -> student -> analytics flow is healthy.")
