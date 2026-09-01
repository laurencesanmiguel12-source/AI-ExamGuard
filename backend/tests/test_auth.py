"""Registration, login, and the role-gated access dependencies (require_admin/instructor/student)
that every other protected route in this app relies on."""


def test_register_creates_a_real_user_and_student_profile(client, make_role, make_course):
    make_role("student")
    course = make_course()
    response = client.post("/auth/register", json={
        "email": "newstudent@example.com",
        "password": "TestPass123!",
        "first_name": "New",
        "last_name": "Student",
        "course_id": course.id,
    })
    assert response.status_code == 200
    body = response.json()
    assert body["email"] == "newstudent@example.com"
    assert "password" not in body
    assert "password_hash" not in body


def test_register_ignores_client_supplied_role_and_always_creates_a_student(client, make_role, make_course):
    make_role("student")
    admin_role = make_role("admin")
    course = make_course()
    response = client.post("/auth/register", json={
        "email": "wannabeadmin@example.com",
        "password": "TestPass123!",
        "first_name": "Sneaky",
        "last_name": "User",
        "course_id": course.id,
        "role_id": admin_role.id,  # not part of the schema anymore - must be ignored, not honored
    })
    assert response.status_code == 200
    response = client.post("/auth/login", json={
        "email": "wannabeadmin@example.com",
        "password": "TestPass123!",
    })
    token = response.json()["access_token"]
    me = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.json()["role_name"] == "student"


def test_register_rejects_unknown_course(client, make_role):
    make_role("student")
    response = client.post("/auth/register", json={
        "email": "newstudent@example.com",
        "password": "TestPass123!",
        "first_name": "New",
        "last_name": "Student",
        "course_id": 999999,
    })
    assert response.status_code == 404


def test_register_rejects_duplicate_email(client, make_role, make_user, make_course):
    make_user("student", email="dupe@example.com")
    make_role("student")
    course = make_course()
    response = client.post("/auth/register", json={
        "email": "dupe@example.com",
        "password": "TestPass123!",
        "first_name": "A",
        "last_name": "B",
        "course_id": course.id,
    })
    assert response.status_code == 400


def test_register_allows_identical_names_in_different_schools(client, make_role, make_school, make_course):
    """Replaces test_register_rejects_duplicate_username. The users table used to carry a
    globally-unique username nothing ever read - login and every lookup key on email - so two
    schools could not both have a "jsmith", and the second one's registration failed with
    "Username already exists." Live symptom: instructors reporting students missing from their
    rosters, because those students had never gotten an account at all. Email stays the one
    unique identifier, and it is unique per person, not per school."""
    make_role("student")
    payload = {"password": "TestPass123!", "first_name": "John", "last_name": "Smith"}

    first = client.post("/auth/register", json={
        **payload, "email": "jsmith@school-a.example.com",
        "course_id": make_course(school=make_school()).id,
    })
    second = client.post("/auth/register", json={
        **payload, "email": "jsmith@school-b.example.com",
        "course_id": make_course(school=make_school()).id,
    })

    assert first.status_code == 200
    assert second.status_code == 200


def test_login_with_correct_credentials_returns_a_token(client, make_user):
    make_user("student", email="login@example.com")
    response = client.post("/auth/login", json={
        "email": "login@example.com",
        "password": "TestPass123!",
    })
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert len(body["access_token"]) > 20


def test_login_with_wrong_password_is_rejected(client, make_user):
    make_user("student", email="wrongpw@example.com")
    response = client.post("/auth/login", json={
        "email": "wrongpw@example.com",
        "password": "not the real password",
    })
    assert response.status_code == 401


def test_login_with_unknown_email_is_rejected(client):
    response = client.post("/auth/login", json={
        "email": "doesnotexist@example.com",
        "password": "whatever",
    })
    assert response.status_code == 401


def test_me_requires_a_token(client):
    response = client.get("/auth/me")
    assert response.status_code in (401, 403)  # HTTPBearer with no header raises 403 in FastAPI


def test_me_rejects_a_garbage_token(client):
    response = client.get("/auth/me", headers={"Authorization": "Bearer not-a-real-jwt"})
    assert response.status_code == 401


def test_me_returns_the_authenticated_user(client, make_user, auth_headers):
    user = make_user("student", email="whoami@example.com")
    response = client.get("/auth/me", headers=auth_headers(user))
    assert response.status_code == 200
    assert response.json()["email"] == "whoami@example.com"


def test_admin_only_route_rejects_a_student(client, make_user, auth_headers):
    student_user = make_user("student")
    response = client.get("/admin/audit-log", headers=auth_headers(student_user))
    assert response.status_code == 403


def test_admin_only_route_accepts_an_admin(client, make_user, auth_headers):
    admin_user = make_user("admin")
    response = client.get("/admin/audit-log", headers=auth_headers(admin_user))
    assert response.status_code == 200


def test_register_rejects_an_email_that_differs_only_in_case(client, make_role, make_course):
    """Real bug found live: registering "Name@gmail.com" when "name@gmail.com" already existed
    returned 200 (a real second account created), not the expected 400 - confirmed against
    production, not assumed. Case-insensitive comparison is what create_user_account is
    supposed to enforce."""
    make_role("student")
    course = make_course()
    first = client.post("/auth/register", json={
        "email": "case.test@example.com", "password": "TestPass123!",
        "first_name": "Case", "last_name": "Test", "course_id": course.id,
    })
    assert first.status_code == 200

    duplicate = client.post("/auth/register", json={
        "email": "CASE.TEST@EXAMPLE.COM", "password": "TestPass123!",
        "first_name": "Case", "last_name": "Duplicate", "course_id": course.id,
    })
    assert duplicate.status_code == 400


def test_login_is_case_insensitive_on_stored_email(client, make_user):
    """The other half of the same bug: an account whose stored email happens to be mixed-case
    (this codebase has a real @gmail.com account like this) was unreachable via login the
    moment someone typed it back in a different case than it was stored in - indistinguishable
    from "not registered" from the user's side."""
    make_user("student", email="MixedCase@Example.com")

    response = client.post("/auth/login", json={
        "email": "mixedcase@example.com",
        "password": "TestPass123!",
    })
    assert response.status_code == 200
    assert "access_token" in response.json()


def test_login_trims_stray_whitespace_on_email(client, make_user):
    make_user("student", email="whitespace@example.com")

    response = client.post("/auth/login", json={
        "email": "  whitespace@example.com  ",
        "password": "TestPass123!",
    })
    assert response.status_code == 200
