"""Outbound email, currently used only to tell platform admins that a school signup is waiting.

Two rules shape everything here:

**Never break the thing that triggered it.** A school registration succeeding must not depend on
an SMTP server being reachable - the applicant has done nothing wrong if our mail provider is
down. Every send is wrapped and logged rather than raised, and callers dispatch it through
FastAPI's BackgroundTasks so a slow or hanging SMTP handshake never holds the HTTP response open.

**Silent by default.** With no SMTP_HOST configured the service logs what it would have sent and
returns. That keeps a fresh clone, CI and the test suite working with no mail server and no
credentials, and makes "email isn't set up" a visible log line instead of a crash.

Uses stdlib smtplib/email deliberately - this project keeps its dependency list short, and nothing
here needs more than that.
"""
import functools
import logging
import smtplib
from email.message import EmailMessage

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.role import Role
from app.models.user import User

logger = logging.getLogger(__name__)


def _never_raises(fn):
    """Applied to every public notify_* entry point, which are what BackgroundTasks actually run.

    send() already swallows the smtplib family, but that is not the whole surface: resolving
    recipients hits the database, and formatting a body touches settings. An exception from any of
    those would propagate out of the background task and fail a request that had already
    succeeded - a school registration turning into a 500 because a mail lookup broke. Guarding the
    outermost call makes "notifications cannot break the triggering action" true by construction
    rather than by remembering to wrap each new step.
    """
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except Exception:
            logger.exception("Notification %s failed; the triggering action is unaffected.", fn.__name__)
            return False
    return wrapper


class NotificationService:

    @staticmethod
    def _recipients(db: Session) -> list[str]:
        """Explicit PLATFORM_NOTIFY_EMAILS wins; otherwise every super_admin's own address, so
        this works out of the box without another setting to keep in sync as operators change."""
        configured = settings.platform_notify_list
        if configured:
            return configured

        rows = (
            db.query(User.email)
            .join(Role, User.role_id == Role.id)
            .filter(Role.name.ilike("super_admin"), User.is_active.is_(True))
            .all()
        )
        return [row[0] for row in rows]

    @staticmethod
    def send(to: list[str], subject: str, body: str) -> bool:
        """Returns whether a message actually went out. Never raises."""
        if not to:
            logger.warning("Email not sent (%r): no recipients resolved.", subject)
            return False

        if not settings.email_enabled:
            logger.info(
                "Email disabled (SMTP_HOST unset). Would have sent %r to %s.", subject, ", ".join(to)
            )
            return False

        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = settings.SMTP_FROM or settings.SMTP_USERNAME
        message["To"] = ", ".join(to)
        message.set_content(body)

        try:
            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as smtp:
                if settings.SMTP_USE_TLS:
                    smtp.starttls()
                if settings.SMTP_USERNAME:
                    smtp.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
                smtp.send_message(message)
            logger.info("Sent %r to %s.", subject, ", ".join(to))
            return True
        except Exception:
            # Deliberately broad: smtplib raises a wide family (auth, connection, DNS, TLS,
            # timeout), and none of them should surface to whoever triggered the notification.
            logger.exception("Failed to send %r to %s.", subject, ", ".join(to))
            return False

    @staticmethod
    def _school_admin_emails(school_id: int, db: Session) -> list[str]:
        rows = (
            db.query(User.email)
            .join(Role, User.role_id == Role.id)
            .filter(
                User.school_id == school_id,
                Role.name.ilike("admin"),  # exact, case-insensitive - does not match super_admin
                User.is_active.is_(True),
            )
            .all()
        )
        return [row[0] for row in rows]

    @staticmethod
    @_never_raises
    def notify_school_approved(school_name: str, school_slug: str, school_id: int,
                               note: str | None, db: Session) -> bool:
        login_url = f"{settings.FRONTEND_BASE_URL.rstrip('/')}/{school_slug}/login"
        body = (
            f"Good news - {school_name} has been approved on AI ExamGuard.\n\n"
            f"You can now sign in with the admin account you registered with:\n"
            f"  {login_url}\n\n"
            + (f"Note from the reviewer: {note}\n\n" if note else "")
            + "Your first steps are to add your courses and subjects, then create instructor "
              "accounts.\n"
        )
        return NotificationService.send(
            NotificationService._school_admin_emails(school_id, db),
            f"[AI ExamGuard] {school_name} has been approved",
            body,
        )

    @staticmethod
    @_never_raises
    def notify_school_rejected(school_name: str, school_id: int, note: str | None,
                               db: Session) -> bool:
        body = (
            f"Your registration for {school_name} on AI ExamGuard was not approved.\n\n"
            + (f"Reason: {note}\n\n" if note else "")
            + "If you believe this was a mistake, reply to this email or contact the platform "
              "administrator.\n"
        )
        return NotificationService.send(
            NotificationService._school_admin_emails(school_id, db),
            f"[AI ExamGuard] Registration not approved: {school_name}",
            body,
        )

    @staticmethod
    @_never_raises
    def notify_school_pending_review(school_name: str, school_code: str, contact_email: str,
                                     db: Session) -> bool:
        review_url = f"{settings.FRONTEND_BASE_URL.rstrip('/')}/school-approvals"
        body = (
            f"A new school has registered on AI ExamGuard and is waiting for review.\n\n"
            f"  School:  {school_name}\n"
            f"  Code:    {school_code}\n"
            f"  Contact: {contact_email}\n\n"
            f"Nobody at this school can sign in until it is approved.\n"
            f"Review it here: {review_url}\n"
        )
        return NotificationService.send(
            NotificationService._recipients(db),
            f"[AI ExamGuard] School pending review: {school_name}",
            body,
        )
