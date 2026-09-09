"""A mistyped provider domain is caught; everything else is left alone.

Context, because the framing matters: general email validation already existed and already
worked. Every schema uses pydantic's EmailStr and it correctly rejects malformed input. What it
cannot reject is `jrizal@gmail.cmo` - found in live production data - because that is valid RFC
syntax. The account simply can never receive a password reset, and nobody finds out until it
matters.

The risk in a guard like this is over-reach: rejecting a legitimate address it has never heard
of would be far worse than the typo it prevents. Most of these tests are about what it must NOT
touch.
"""
import pytest

from app.schemas.email_typo import check_email_typo, suggest_domain_correction


@pytest.mark.parametrize("address, expected", [
    # The real one, from live data. A transposition - the reason plain Levenshtein is not enough.
    ("jrizal@gmail.cmo", "gmail.com"),
    ("a@gmail.con", "gmail.com"),
    ("a@gmial.com", "gmail.com"),
    ("a@gmail.co", "gmail.com"),
    ("a@yahoo.cm", "yahoo.com"),
    ("a@hotmail.con", "hotmail.com"),
    ("a@outlook.cm", "outlook.com"),
])
def test_catches_a_near_miss_on_a_known_provider(address, expected):
    assert suggest_domain_correction(address) == expected


@pytest.mark.parametrize("address", [
    "ana@gmail.com",
    "ana@yahoo.com",
    "ana@outlook.com",
    "ana@hotmail.com",
    "ana@icloud.com",
])
def test_leaves_a_correct_provider_alone(address):
    assert suggest_domain_correction(address) is None


@pytest.mark.parametrize("address", [
    # Institutional domains are the common case here and must pass untouched - this guard must
    # never become a gatekeeper on domains it simply has not heard of.
    "staff@arellano.edu.ph",
    "dean@earist.edu.ph",
    "x@my-college.edu",
    "someone@some-startup.io",
    "person@mail.example.org",
])
def test_leaves_an_unknown_domain_completely_alone(address):
    assert suggest_domain_correction(address) is None


def test_a_domain_that_merely_resembles_nothing_is_not_corrected():
    # Two or more edits away is not a confident typo, so it is left alone rather than guessed at.
    assert suggest_domain_correction("a@gmoil.cwm") is None


def test_the_error_names_the_correction():
    with pytest.raises(ValueError) as caught:
        check_email_typo("jrizal@gmail.cmo")

    message = str(caught.value)
    assert "gmail.com" in message, "an error that doesn't say what to type instead is a dead end"
    assert "password reset" in message, "say why it matters, not just that it's wrong"


def test_a_correct_address_raises_nothing():
    check_email_typo("ana@arellano.edu.ph")
    check_email_typo("ana@gmail.com")


@pytest.mark.parametrize("junk", ["", "not-an-email", "@", "no-at-sign.com"])
def test_malformed_input_is_not_this_check_s_job(junk):
    # EmailStr rejects these long before this runs; it must not crash on them either way.
    assert suggest_domain_correction(junk) is None


def test_case_and_whitespace_do_not_hide_a_typo():
    assert suggest_domain_correction("A@GMAIL.CMO") == "gmail.com"
    assert suggest_domain_correction("a@gmail.cmo ") == "gmail.com"


def test_the_guard_is_applied_to_account_creation():
    from app.schemas.instructor import InstructorCreate

    with pytest.raises(Exception):
        InstructorCreate(
            employee_number="E1", email="jrizal@gmail.cmo",
            password="TestPass123!", first_name="Jose", last_name="Rizal",
        )


def test_the_guard_is_not_applied_to_signing_in():
    """Someone whose stored address already has the typo must still be able to log in - locking
    them out would turn a bad email into a lost account."""
    from app.schemas.auth import LoginRequest

    assert LoginRequest(email="jrizal@gmail.cmo", password="x").email == "jrizal@gmail.cmo"
