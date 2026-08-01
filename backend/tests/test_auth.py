"""Registration, login, and the role-gated access dependencies (require_admin/instructor/student)
that every other protected route in this app relies on."""


def test_register_creates_a_real_user(client, make_role):
    role = make_role("student")
    response = client.post("/auth/register", json={
        "username": "newstudent",
        "email": "newstudent@example.com",
        "password": "TestPass123!",
        "first_name": "New",
        "last_name": "Student",
        "role_id": role.id,
    })
    assert response.status_code == 200
    body = response.json()
    assert body["email"] == "newstudent@example.com"
    assert "password" not in body
    assert "password_hash" not in body


def test_register_rejects_duplicate_email(client, make_role, make_user):
    make_user("student", email="dupe@example.com")
    role = make_role("student")
    response = client.post("/auth/register", json={
        "username": "someoneelse",
        "email": "dupe@example.com",
        "password": "TestPass123!",
        "first_name": "A",
        "last_name": "B",
        "role_id": role.id,
    })
    assert response.status_code == 400


def test_register_rejects_duplicate_username(client, make_role, make_user):
    make_user("student", username="taken")
    role = make_role("student")
    response = client.post("/auth/register", json={
        "username": "taken",
        "email": "different@example.com",
        "password": "TestPass123!",
        "first_name": "A",
        "last_name": "B",
        "role_id": role.id,
    })
    assert response.status_code == 400


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
