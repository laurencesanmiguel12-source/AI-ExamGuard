"""Shared pytest fixtures for the backend test suite.

**Test database, not the dev one**: reads backend/.env's DATABASE_URL (same credentials the dev
server uses) but swaps the trailing database name to `ai_examguard_test` - a real, separate
Postgres database created once (see ai_examguard_project_status memory) rather than SQLite, since
this app uses real Postgres in every other environment and behavior can differ in ways that matter
(e.g. server_default handling, real FK enforcement). CI creates this same database fresh inside a
Postgres service container - see .github/workflows/tests.yml.

**Isolation, not full setup/teardown per test**: schema is created once per test session
(Base.metadata.create_all - faster than running every Alembic migration, and this project already
has a separate check that migrations match the models via a real docker-compose run, see
ai_examguard_fairness... no, project_status memory's Docker section). Each individual test runs
inside its own transaction that's rolled back afterward, so tests never see each other's data and
don't need to manually clean up.
"""
import os
import re

os.environ["ALLOWED_ORIGINS"] = "http://localhost:5173"

_env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
with open(_env_path) as f:
    for line in f:
        if line.startswith("DATABASE_URL="):
            _dev_url = line.strip().split("=", 1)[1]
            os.environ["DATABASE_URL"] = re.sub(r"/[^/]+$", "/ai_examguard_test", _dev_url)
            break
    else:
        raise RuntimeError(f"No DATABASE_URL line found in {_env_path}")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

import app.models  # noqa: E402, F401 - registers every model on Base.metadata before create_all
from app.auth.jwt import create_access_token  # noqa: E402
from app.auth.security import hash_password  # noqa: E402
from app.core.database import get_db  # noqa: E402
from app.main import app as fastapi_app  # noqa: E402
from app.models.base import Base  # noqa: E402
from app.models.course import Course  # noqa: E402
from app.models.exam import Exam  # noqa: E402
from app.models.instructor import Instructor  # noqa: E402
from app.models.instructor_subject import InstructorSubject  # noqa: E402
from app.models.role import Role  # noqa: E402
from app.models.school import School  # noqa: E402
from app.models.student import Student  # noqa: E402
from app.models.subject import Subject  # noqa: E402
from app.models.user import User  # noqa: E402

engine = create_engine(os.environ["DATABASE_URL"])
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# bcrypt hashing is deliberately slow (that's the point, in production) - hash the shared test
# password once at import time instead of once per make_user() call, or the suite crawls.
TEST_PASSWORD = "TestPass123!"
TEST_PASSWORD_HASH = hash_password(TEST_PASSWORD)


@pytest.fixture(scope="session", autouse=True)
def _create_schema():
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)


@pytest.fixture
def db(_create_schema):
    """A DB session bound to a single transaction that's rolled back after the test - real Postgres
    semantics (constraints, defaults) with no cross-test leakage and no per-test schema churn."""
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def client(db):
    """TestClient with get_db overridden to use the same rolled-back-after transaction as the `db`
    fixture, so setup done directly via `db` and assertions made via API calls see the same data."""
    def _override_get_db():
        yield db

    fastapi_app.dependency_overrides[get_db] = _override_get_db
    with TestClient(fastapi_app) as c:
        yield c
    fastapi_app.dependency_overrides.clear()


# ---- Factory fixtures - create real rows via the ORM, fast, no API round-trip needed for setup ----

@pytest.fixture
def make_role(db):
    def _make(name: str) -> Role:
        role = db.query(Role).filter(Role.name == name).first()
        if role is None:
            role = Role(name=name)
            db.add(role)
            db.commit()
            db.refresh(role)
        return role
    return _make


@pytest.fixture
def make_school(db):
    counter = {"n": 0}

    def _make(**overrides) -> School:
        counter["n"] += 1
        n = counter["n"]
        defaults = dict(code=f"SCH{n}", name=f"Test School {n}", slug=f"test-school-{n}")
        defaults.update(overrides)
        school = School(**defaults)
        db.add(school)
        db.commit()
        db.refresh(school)
        return school
    return _make


@pytest.fixture
def default_school(make_school):
    """Most tests don't care about multi-tenancy - they just need every fixture's school_id to
    agree so single-school assumptions (a student's course matches their own school, etc.) hold
    without every test having to wire it up explicitly. Tests that actually exercise cross-school
    behavior call make_school() again and pass school= explicitly to the fixtures below."""
    return make_school()


@pytest.fixture
def make_user(db, make_role, default_school):
    counter = {"n": 0}

    def _make(role_name: str, **overrides) -> User:
        counter["n"] += 1
        n = counter["n"]
        role = make_role(role_name)
        school = overrides.pop("school", None) or default_school
        defaults = dict(
            username=f"user{n}",
            email=f"user{n}@example.com",
            first_name="Test",
            last_name=f"User{n}",
            password_hash=TEST_PASSWORD_HASH,
            role_id=role.id,
            school_id=school.id,
            is_active=True,
        )
        defaults.update(overrides)
        user = User(**defaults)
        db.add(user)
        db.commit()
        db.refresh(user)
        return user
    return _make


@pytest.fixture
def make_course(db, default_school):
    counter = {"n": 0}

    def _make(school=None, **overrides) -> Course:
        counter["n"] += 1
        n = counter["n"]
        if school is None:
            school = default_school
        defaults = dict(code=f"COURSE{n}", name=f"Test Course {n}", school_id=school.id)
        defaults.update(overrides)
        course = Course(**defaults)
        db.add(course)
        db.commit()
        db.refresh(course)
        return course
    return _make


@pytest.fixture
def make_subject(db, make_course):
    counter = {"n": 0}

    def _make(course=None, **overrides) -> Subject:
        counter["n"] += 1
        n = counter["n"]
        if course is None:
            course = make_course()
        defaults = dict(code=f"SUBJ{n}", name=f"Test Subject {n}", course_id=course.id)
        defaults.update(overrides)
        subject = Subject(**defaults)
        db.add(subject)
        db.commit()
        db.refresh(subject)
        return subject
    return _make


@pytest.fixture
def make_instructor(db, make_user):
    counter = {"n": 0}

    def _make(**overrides) -> Instructor:
        counter["n"] += 1
        n = counter["n"]
        user = overrides.pop("user", None) or make_user("instructor")
        defaults = dict(employee_number=f"EMP-{n:04d}", user_id=user.id)
        defaults.update(overrides)
        instructor = Instructor(**defaults)
        db.add(instructor)
        db.commit()
        db.refresh(instructor)
        instructor.user = user
        return instructor
    return _make


@pytest.fixture
def make_instructor_subject(db):
    def _make(instructor, subject) -> InstructorSubject:
        entry = InstructorSubject(instructor_id=instructor.id, subject_id=subject.id)
        db.add(entry)
        db.commit()
        db.refresh(entry)
        return entry
    return _make


@pytest.fixture
def make_student(db, make_user, make_course):
    counter = {"n": 0}

    def _make(**overrides) -> Student:
        counter["n"] += 1
        n = counter["n"]
        user = overrides.pop("user", None) or make_user("student")
        course = overrides.pop("course", None) or make_course()
        # skip_face_check=True by default - these fixtures build students for exam-flow tests,
        # not face-enrollment tests, and exam start now requires either an enrolled face model
        # or this flag (see ExamSessionService.start_exam) - override explicitly for tests that
        # exercise the enrollment gate itself.
        defaults = dict(
            student_number=f"2026-{n:04d}", user_id=user.id, course_id=course.id,
            skip_face_check=True,
        )
        defaults.update(overrides)
        student = Student(**defaults)
        db.add(student)
        db.commit()
        db.refresh(student)
        student.user = user
        return student
    return _make


@pytest.fixture
def make_exam(db, make_instructor, make_subject):
    from datetime import datetime, timedelta, timezone
    counter = {"n": 0}

    def _make(**overrides) -> Exam:
        counter["n"] += 1
        n = counter["n"]
        instructor = overrides.pop("instructor", None) or make_instructor()
        subject = overrides.pop("subject", None) or make_subject()
        now = datetime.now(timezone.utc)
        defaults = dict(
            title=f"Test Exam {n}",
            duration_minutes=30,
            total_points=0,
            passing_score=50,
            start_time=now - timedelta(hours=1),
            end_time=now + timedelta(hours=1),
            is_active=True,
            subject_id=subject.id,
            instructor_id=instructor.id,
        )
        defaults.update(overrides)
        exam = Exam(**defaults)
        db.add(exam)
        db.commit()
        db.refresh(exam)
        return exam
    return _make


@pytest.fixture
def auth_headers():
    def _make(user: User) -> dict:
        token = create_access_token({"sub": user.email})
        return {"Authorization": f"Bearer {token}"}
    return _make
