"""Infrastructure smoke test - if this fails, the fixtures are broken, not the app."""


def test_health_check(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "running"


def test_make_student_fixture_works(make_student):
    student = make_student()
    assert student.id is not None
    assert student.user.role.name == "student"


def test_auth_headers_are_accepted(client, make_user, auth_headers):
    user = make_user("admin")
    response = client.get("/exams/", headers=auth_headers(user))
    assert response.status_code == 200
