"""Self-service school signup is a request to join the platform, not an instant tenancy: a super
admin approves it before anyone at that school can log in. See SchoolService.register /
AuthService.login's status check.

test_multi_tenancy.py::test_school_signup_creates_a_working_admin_account covers the happy path
end to end (signup -> blocked -> approve -> login -> create a course). These cover the edges.
"""


def _register(client, code="APPU", slug="approval-university", email="founder@approval.example.com"):
    return client.post("/schools/register", json={
        "code": code,
        "name": "Approval University",
        "slug": slug,
        "email": email,
        "password": "TestPass123!",
        "first_name": "Ada",
        "last_name": "Founder",
    })


def test_signup_creates_the_school_as_pending(client, make_role):
    make_role("admin")

    response = _register(client)

    assert response.status_code == 200
    assert response.json()["status"] == "pending"


def test_pending_school_is_hidden_from_the_public_school_list(client, make_role):
    """That list feeds the student-registration picker - a school whose own admin cannot log in
    yet must not be selectable."""
    make_role("admin")
    _register(client)

    listed = client.get("/schools/")

    assert listed.status_code == 200
    assert "approval-university" not in [s["slug"] for s in listed.json()]


def test_pending_school_is_still_resolvable_by_slug_so_its_login_page_can_explain(client, make_role):
    """Deliberately not hidden here: the applicant following their own signup link needs to be
    told the registration is under review, not bounced as though the school never existed."""
    make_role("admin")
    _register(client)

    response = client.get("/schools/slug/approval-university")

    assert response.status_code == 200
    assert response.json()["status"] == "pending"
    assert response.json()["name"] == "Approval University"


def test_rejected_school_login_surfaces_the_reviewers_reason(client, make_role, make_user, auth_headers):
    make_role("admin")
    school_id = _register(client).json()["id"]
    super_admin = make_user("super_admin")

    rejected = client.put(
        f"/schools/{school_id}/review", headers=auth_headers(super_admin),
        json={"status": "rejected", "review_note": "Not a recognised institution."},
    )
    assert rejected.status_code == 200

    login = client.post("/auth/login", json={
        "email": "founder@approval.example.com", "password": "TestPass123!",
    })
    assert login.status_code == 403
    assert "Not a recognised institution." in login.json()["detail"]


def test_a_school_cannot_be_reviewed_twice(client, make_role, make_user, auth_headers):
    make_role("admin")
    school_id = _register(client).json()["id"]
    super_admin = make_user("super_admin")
    headers = auth_headers(super_admin)

    first = client.put(f"/schools/{school_id}/review", headers=headers, json={"status": "approved"})
    assert first.status_code == 200

    second = client.put(f"/schools/{school_id}/review", headers=headers, json={"status": "rejected"})
    assert second.status_code == 400
    assert "already been reviewed" in second.json()["detail"]


def test_review_rejects_a_nonsense_status(client, make_role, make_user, auth_headers):
    make_role("admin")
    school_id = _register(client).json()["id"]
    super_admin = make_user("super_admin")

    response = client.put(
        f"/schools/{school_id}/review", headers=auth_headers(super_admin),
        json={"status": "pending"},  # not a decision
    )

    assert response.status_code == 400


def test_a_regular_admin_cannot_review_schools(client, make_role, make_user, auth_headers):
    make_role("admin")
    school_id = _register(client).json()["id"]
    admin = make_user("admin")

    response = client.put(
        f"/schools/{school_id}/review", headers=auth_headers(admin), json={"status": "approved"}
    )

    assert response.status_code == 403


def test_review_queue_is_super_admin_only_and_shows_pending_schools(
    client, make_role, make_user, auth_headers
):
    make_role("admin")
    _register(client)
    admin = make_user("admin")
    super_admin = make_user("super_admin")

    assert client.get("/schools/review", headers=auth_headers(admin)).status_code == 403

    queue = client.get("/schools/review?status=pending", headers=auth_headers(super_admin))
    assert queue.status_code == 200
    assert "approval-university" in [s["slug"] for s in queue.json()]


def test_students_cannot_self_register_into_a_pending_school(
    client, make_role, make_school, make_course
):
    """GET /schools/ hides it from the picker, but this endpoint is public - a course_id from a
    pending school can still be posted directly."""
    make_role("student")
    pending_school = make_school(status="pending")
    course = make_course(school=pending_school)

    response = client.post("/auth/register", json={
        "email": "hopeful@example.com",
        "password": "TestPass123!",
        "first_name": "Hope",
        "last_name": "Ful",
        "course_id": course.id,
    })

    assert response.status_code == 403
    assert "not accepting registrations" in response.json()["detail"]


def test_super_admin_can_still_log_in_when_their_own_school_is_pending(
    client, make_user, make_school
):
    """A super admin is who reviews the queue - being scoped to a pending school must not lock
    them out of the platform, same carve-out the is_active check already has."""
    pending_school = make_school(status="pending")
    make_user("super_admin", school=pending_school, email="platform@example.com")

    response = client.post("/auth/login", json={
        "email": "platform@example.com", "password": "TestPass123!",
    })

    assert response.status_code == 200
