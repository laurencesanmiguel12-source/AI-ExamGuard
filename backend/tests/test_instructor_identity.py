"""Instructors are identifiable, and distinguishable from each other.

Two defense-panel reports, one page:

  "Instructor should have complete information especially the Name"
  "an instructor can be assigned on same subjects, there is no way to differentiate which one
   each instructor is managing, current system shows only subject and has no course assigned"

Both traced to InstructorResponse, which carried only employee_number, user_id and id - so the
table physically could not print a name, and a subject code arrived with no course context.
"""
from app.schemas.instructor import InstructorResponse


def test_the_response_carries_a_human_name(db, make_instructor, make_user):
    user = make_user("instructor", first_name="Noelito", last_name="Francisco")
    instructor = make_instructor(user=user)

    payload = InstructorResponse.model_validate(instructor)

    assert payload.instructor_name == "Noelito Francisco"


def test_the_response_carries_the_email(db, make_instructor, make_user):
    user = make_user("instructor", email="nfrancisco@school.edu")
    instructor = make_instructor(user=user)

    assert InstructorResponse.model_validate(instructor).email == "nfrancisco@school.edu"


def test_each_assignment_names_its_course_not_just_the_subject(
    db, make_instructor, make_subject, make_instructor_subject
):
    subject = make_subject(code="CS-101", name="Programming 1")
    instructor = make_instructor()
    make_instructor_subject(instructor, subject)
    db.refresh(instructor)

    payload = InstructorResponse.model_validate(instructor)

    assert len(payload.assignments) == 1
    assignment = payload.assignments[0]
    assert assignment.subject_code == "CS-101"
    # The whole point of the panel's second report: a bare subject code is ambiguous.
    assert assignment.course_code is not None
    assert assignment.course_id == subject.course_id


def test_two_instructors_on_the_same_subject_are_distinguishable(
    db, make_instructor, make_user, make_subject, make_instructor_subject
):
    subject = make_subject(code="CS-101", name="Programming 1")
    first = make_instructor(user=make_user("instructor", first_name="Ana", last_name="Cruz"))
    second = make_instructor(user=make_user("instructor", first_name="Ben", last_name="Reyes"))
    make_instructor_subject(first, subject)
    make_instructor_subject(second, subject)
    db.refresh(first)
    db.refresh(second)

    a = InstructorResponse.model_validate(first)
    b = InstructorResponse.model_validate(second)

    # Same subject, but the rows are no longer interchangeable on screen.
    assert a.assignments[0].subject_code == b.assignments[0].subject_code
    assert a.instructor_name != b.instructor_name
    assert {a.instructor_name, b.instructor_name} == {"Ana Cruz", "Ben Reyes"}


def test_an_instructor_with_no_subjects_reports_none_rather_than_failing(db, make_instructor):
    instructor = make_instructor()

    payload = InstructorResponse.model_validate(instructor)

    assert payload.assignments == []
    assert payload.instructor_name is not None


def test_assignments_are_ordered_by_course_then_subject(
    db, make_instructor, make_course, make_subject, make_instructor_subject
):
    """Grouped by course first, because that is how the list is read - all of one course's
    subjects together - and only then alphabetically within it."""
    instructor = make_instructor()
    bscs = make_course(code="BSCS", name="BS Computer Science")
    bsit = make_course(code="BSIT", name="BS Information Technology")
    for course, code in [(bsit, "IT-201"), (bscs, "CS-301"), (bsit, "IT-101"), (bscs, "CS-101")]:
        make_instructor_subject(instructor, make_subject(course=course, code=code, name=code))
    db.refresh(instructor)

    pairs = [
        (a.course_code, a.subject_code)
        for a in InstructorResponse.model_validate(instructor).assignments
    ]

    assert pairs == [
        ("BSCS", "CS-101"), ("BSCS", "CS-301"),
        ("BSIT", "IT-101"), ("BSIT", "IT-201"),
    ]
