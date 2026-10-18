# D:\FYP\FORGE-1\backend\services\mailer.py
"""
Sends FORGE's emails: verify your address, reset your password (D-187).

Mail goes out over SMTP with STARTTLS (port 587) or TLS (port 465), using the settings in .env.
Routes queue a message to be sent after the HTTP answer, so a slow mail server never delays the
user and a failed send is logged, not shown. Without SMTP_HOST (local development) the message,
including its link, is written to the log instead. Tests replace `deliver`.
"""
import html
import logging
import smtplib
import ssl
from dataclasses import dataclass
from email.message import EmailMessage

from fastapi.concurrency import run_in_threadpool

from backend.core.config import settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class OutgoingEmail:
    to: str
    subject: str
    text: str
    html: str


def deliver(message: OutgoingEmail) -> None:
    """Send one email (blocking). Raises on failure."""
    if not settings.SMTP_HOST:
        logger.warning("SMTP is not configured; email to %s not sent:\n%s", message.to, message.text)
        return
    mail = EmailMessage()
    mail["From"] = settings.MAIL_FROM or settings.SMTP_USERNAME
    mail["To"] = message.to
    mail["Subject"] = message.subject
    mail.set_content(message.text)
    mail.add_alternative(message.html, subtype="html")
    context = ssl.create_default_context()
    if settings.SMTP_PORT == 465:
        with smtplib.SMTP_SSL(settings.SMTP_HOST, 465, timeout=20, context=context) as server:
            server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            server.send_message(mail)
    else:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=20) as server:
            server.starttls(context=context)
            server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            server.send_message(mail)


async def send(message: OutgoingEmail) -> None:
    """Send without blocking the server; failures are logged (the user can ask for a new email)."""
    try:
        await run_in_threadpool(deliver, message)
    except Exception:
        logger.exception("Could not send '%s' to %s", message.subject, message.to)


def _layout(name: str, intro: str, button: str, link: str, footer: str) -> tuple[str, str]:
    text = f"Hello {name},\n\n{intro}\n\n{button}: {link}\n\n{footer}\n\n- FORGE"
    safe_link = html.escape(link, quote=True)
    body = f"""<div style="font-family:Arial,sans-serif;max-width:520px;margin:auto;color:#1f1c18">
  <p style="font-size:18px;font-weight:bold;letter-spacing:3px">FORGE</p>
  <p>Hello {html.escape(name)},</p>
  <p>{html.escape(intro)}</p>
  <p><a href="{safe_link}" style="display:inline-block;background:#b0522b;color:#ffffff;padding:12px 20px;border-radius:8px;text-decoration:none;font-weight:bold">{html.escape(button)}</a></p>
  <p style="font-size:13px;color:#645d53">If the button does not work, copy this link into your browser:<br>{safe_link}</p>
  <p style="font-size:13px;color:#645d53">{html.escape(footer)}</p>
</div>"""
    return text, body


def verification_email(to: str, name: str, link: str) -> OutgoingEmail:
    text, body = _layout(name, "Please confirm your email address to start building websites with FORGE.",
                         "Verify my email", link, "This link works once and expires in 24 hours. If you did not create a FORGE account, you can ignore this email.")
    return OutgoingEmail(to, "Verify your email for FORGE", text, body)


def reset_email(to: str, name: str, link: str) -> OutgoingEmail:
    text, body = _layout(name, "We received a request to reset your FORGE password.",
                         "Choose a new password", link, "This link works once and expires in 30 minutes. If you did not ask for this, you can ignore this email; your password stays the same.")
    return OutgoingEmail(to, "Reset your FORGE password", text, body)
