import logging
import smtplib
from email.message import EmailMessage

from ..config import Settings

log = logging.getLogger("app.mail")


def send_mail(settings: Settings, to: str, subject: str, body: str) -> None:
    """MAIL_BACKEND=console prints the mail to the server log (development). smtp sends it for real."""
    if settings.mail_backend == "smtp" and settings.smtp_host:
        msg = EmailMessage()
        msg["From"], msg["To"], msg["Subject"] = settings.mail_from, to, subject
        msg.set_content(body)
        try:
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as s:
                s.starttls()
                if settings.smtp_user:
                    s.login(settings.smtp_user, settings.smtp_password)
                s.send_message(msg)
        except Exception:
            log.exception("Could not send mail to %s", to)
        return
    log.info("MAIL to=%s subject=%s\n%s", to, subject, body)
