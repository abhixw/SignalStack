import logging
import smtplib
from email.mime.text import MIMEText

from app.config.config import config

logger = logging.getLogger("signalstack.email")


def send_email(to_email: str, subject: str, body: str) -> bool:
    """Blocking (smtplib has no async API) — callers on the event loop must
    run this via asyncio.to_thread. Returns False on any failure rather than
    raising, since a delivery failure must never surface as a 500 to the
    caller of /auth/forgot-password (which always returns a generic response
    to avoid leaking whether an email address is registered)."""
    if not config.SMTP_HOST:
        logger.warning(
            "SMTP_HOST not configured — email NOT sent to %s (subject: %s).",
            to_email, subject,
        )
        if not config.IS_PRODUCTION:
            # Dev/local convenience only: surface the OTP/body in server logs so
            # the flow is testable without real SMTP credentials.
            logger.warning("[DEV ONLY] Would have sent:\n%s", body)
        return False

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = config.SMTP_FROM_EMAIL or config.SMTP_USER
    msg["To"] = to_email

    try:
        with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT, timeout=10) as server:
            if config.SMTP_USE_TLS:
                server.starttls()
            if config.SMTP_USER:
                server.login(config.SMTP_USER, config.SMTP_PASSWORD)
            server.sendmail(msg["From"], [to_email], msg.as_string())
        return True
    except Exception as e:
        # Never let SMTP host/credentials leak into logs beyond what smtplib
        # itself includes in its exception message (it doesn't echo the password).
        logger.error("Failed to send email to %s: %s", to_email, e)
        return False
