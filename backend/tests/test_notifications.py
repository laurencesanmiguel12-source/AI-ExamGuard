"""Email notifications for the school-approval flow.

The hard requirement these protect: a notification must never be able to break the action that
triggered it. School signup is public and unauthenticated, and approving a school is a decision a
super admin already committed - neither may turn into a 500 because an SMTP server is unreachable
or was never configured.

Nothing here talks to a real mail server. SMTP_HOST is empty in the test environment, so
NotificationService.send short-circuits; where a test needs to know a notification was attempted,
it patches send() and inspects the call.
"""
import pytest

from app.core.config import settings
from app.services.notification_service import NotificationService


@pytest.fixture(autouse=True)
def unconfigured_email(monkeypatch):
    """Pin the email settings for every test in this module.

    These originally just read whatever was in backend/.env, which meant the suite's result
    depended on whether the developer had configured SMTP yet: green on CI and on a fresh clone,
    red the moment real Gmail credentials were added. Tests must not care about ambient config -
    anything that needs a specific setting overrides it explicitly below.
    """
    monkeypatch.setattr(settings, "SMTP_HOST", "")
    monkeypatch.setattr(settings, "PLATFORM_NOTIFY_EMAILS", "")


@pytest.fixture
def sent(monkeypatch):
    """Captures (recipients, subject, body) instead of sending."""
    calls = []

    def _capture(to, subject, body):
        calls.append({"to": to, "subject": subject, "body": body})
        return True

    monkeypatch.setattr(NotificationService, "send", staticmethod(_capture))
    return calls


def _register(client, code="NOTIFYU", slug="notify-university", email="founder@notify.example.com"):
    return client.post("/schools/register", json={
        "code": code, "name": "Notify University", "slug": slug,
        "email": email, "password": "TestPass123!",
        "first_name": "Nora", "last_name": "Founder",
    })


def test_send_is_a_noop_when_smtp_is_not_configured(db):
    """A fresh clone has no SMTP settings at all - that must be a logged no-op, not an exception."""
    assert settings.email_enabled is False

    assert NotificationService.send(["someone@example.com"], "Subject", "Body") is False


def test_configured_recipients_win_over_the_super_admin_fallback(db, make_user, monkeypatch):
    """The deployed config sets PLATFORM_NOTIFY_EMAILS because the super admin's own address is
    on a domain with no MX records - the fallback would post alerts into a void."""
    make_user("super_admin", email="platform.one@example.com")
    monkeypatch.setattr(settings, "PLATFORM_NOTIFY_EMAILS", "ops@example.com, second@example.com")

    assert NotificationService._recipients(db) == ["ops@example.com", "second@example.com"]


def test_send_with_no_recipients_does_not_raise(db):
    assert NotificationService.send([], "Subject", "Body") is False


def test_recipients_fall_back_to_super_admin_addresses(db, make_user):
    """PLATFORM_NOTIFY_EMAILS is empty by default, so alerts should still reach whoever actually
    operates the platform without another setting to maintain."""
    make_user("super_admin", email="platform.one@example.com")
    make_user("admin", email="school.admin@example.com")

    recipients = NotificationService._recipients(db)

    assert "platform.one@example.com" in recipients
    assert "school.admin@example.com" not in recipients


def test_school_signup_notifies_the_platform(client, make_role, make_user, sent):
    make_role("admin")
    make_user("super_admin", email="platform.one@example.com")

    assert _register(client).status_code == 200

    assert len(sent) == 1
    assert "Notify University" in sent[0]["subject"]
    assert "platform.one@example.com" in sent[0]["to"]


def test_signup_still_succeeds_when_sending_blows_up(client, make_role, make_user, monkeypatch):
    """The applicant did nothing wrong if our mail provider is down."""
    make_role("admin")
    make_user("super_admin", email="platform.one@example.com")

    def _explode(*_args, **_kwargs):
        raise RuntimeError("SMTP is on fire")

    monkeypatch.setattr(NotificationService, "send", staticmethod(_explode))

    # BackgroundTasks run inside the TestClient request; the response must still be a clean 200
    # because NotificationService swallows its own failures.
    response = _register(client)

    assert response.status_code == 200
    assert response.json()["status"] == "pending"


def test_approving_a_school_notifies_that_schools_admin(client, make_role, make_user, auth_headers, sent):
    make_role("admin")
    school_id = _register(client).json()["id"]
    super_admin = make_user("super_admin")
    sent.clear()  # drop the signup notification

    response = client.put(
        f"/schools/{school_id}/review", headers=auth_headers(super_admin),
        json={"status": "approved"},
    )
    assert response.status_code == 200

    assert len(sent) == 1
    assert "founder@notify.example.com" in sent[0]["to"]
    assert "approved" in sent[0]["subject"]
    assert "/notify-university/login" in sent[0]["body"]


def test_rejecting_a_school_emails_the_reason(client, make_role, make_user, auth_headers, sent):
    make_role("admin")
    school_id = _register(client).json()["id"]
    super_admin = make_user("super_admin")
    sent.clear()

    client.put(
        f"/schools/{school_id}/review", headers=auth_headers(super_admin),
        json={"status": "rejected", "review_note": "Could not verify this institution."},
    )

    assert len(sent) == 1
    assert "founder@notify.example.com" in sent[0]["to"]
    assert "not approved" in sent[0]["subject"].lower()
    assert "Could not verify this institution." in sent[0]["body"]


def test_the_decision_email_goes_to_the_school_not_the_platform(
    client, make_role, make_user, auth_headers, sent
):
    """Regression guard on the recipient lookup: _school_admin_emails matches "admin" exactly, so
    a super admin (whose role name merely contains "admin") must not be swept in."""
    make_role("admin")
    school_id = _register(client).json()["id"]
    super_admin = make_user("super_admin", email="platform.one@example.com")
    sent.clear()

    client.put(
        f"/schools/{school_id}/review", headers=auth_headers(super_admin),
        json={"status": "approved"},
    )

    assert sent[0]["to"] == ["founder@notify.example.com"]
