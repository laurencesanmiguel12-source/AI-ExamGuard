"""GET /courses/{id} is not public, unlike the list beside it.

Found in a backend sweep for routes with no auth dependency. The LIST is deliberately open - a
visitor has to populate a registration dropdown before they have an account - and it is scoped by
a required school_id parameter, so it can only ever return one school's catalogue. The detail
route took a bare id and returned whatever it found, which made every school's course codes and
names enumerable by anyone who could count. Nothing in the app called it.
"""


def test_course_detail_requires_a_signed_in_caller(client, make_course):
    course = make_course(code="BSCS", name="BS Computer Science")

    response = client.get(f"/courses/{course.id}")

    assert response.status_code in (401, 403)


def test_the_list_is_still_public_for_the_registration_dropdown(client, default_school, make_course):
    """The reason the list is open in the first place - breaking it would break signup."""
    make_course(code="BSCS", name="BS Computer Science")

    response = client.get("/courses/", params={"school_id": default_school.id})

    assert response.status_code == 200
    assert [c["code"] for c in response.json()] == ["BSCS"]


def test_a_signed_in_user_can_read_a_course_in_their_own_school(
    client, make_course, make_user, auth_headers
):
    course = make_course(code="BSCS", name="BS Computer Science")
    user = make_user("instructor")

    response = client.get(f"/courses/{course.id}", headers=auth_headers(user))

    assert response.status_code == 200
    assert response.json()["code"] == "BSCS"


def test_another_schools_course_reads_as_missing_rather_than_forbidden(
    client, make_course, make_school, make_user, auth_headers
):
    """404, not 403: "that course exists but is not yours" is itself worth not saying, and the
    caller cannot act on the difference either way."""
    foreign = make_course(code="SECRET", name="Other University Programme",
                          school=make_school(name="Other University"))
    user = make_user("admin")

    response = client.get(f"/courses/{foreign.id}", headers=auth_headers(user))

    assert response.status_code == 404
    assert "SECRET" not in response.text


def test_a_super_admin_may_read_any_schools_course(
    client, make_course, make_school, make_user, auth_headers
):
    foreign = make_course(code="BSIT", school=make_school(name="Other University"))
    superadmin = make_user("super_admin")

    response = client.get(f"/courses/{foreign.id}", headers=auth_headers(superadmin))

    assert response.status_code == 200
