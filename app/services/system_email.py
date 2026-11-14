"""Email ARC itself sends to its own users (password resets today).

Separate from outreach (D18): outreach goes out from each client's own
Brevo/Resend account; this uses one platform-level account set with
SYSTEM_EMAIL_PROVIDER, SYSTEM_EMAIL_API_KEY and SYSTEM_EMAIL_FROM. Without
all three, nothing is sent and `send_system_email` returns False.
"""

import logging
import uuid
from html import escape

from flask import current_app

from app.integrations.email_providers import PROVIDERS, EmailProviderError

log = logging.getLogger("app.system_email")


def is_configured() -> bool:
    cfg = current_app.config
    return bool(cfg.get("SYSTEM_EMAIL_PROVIDER") in PROVIDERS and cfg.get("SYSTEM_EMAIL_API_KEY")
                and cfg.get("SYSTEM_EMAIL_FROM"))


def send_system_email(to_email: str, subject: str, paragraphs: list[str], link: str | None = None,
                      link_label: str = "Open ARC") -> bool:
    """Returns True only when the provider accepted the message. Never raises:
    callers such as forgot-password must respond the same way either way."""

    if not is_configured():
        log.warning("System email not configured; '%s' was not sent.", subject)
        return False
    cfg = current_app.config
    text = "\n\n".join(paragraphs + ([f"{link_label}: {link}"] if link else []))
    html = "".join(f"<p>{escape(p)}</p>" for p in paragraphs)
    if link:
        html += f'<p><a href="{escape(link, quote=True)}">{escape(link_label)}</a></p>'
    sender = PROVIDERS[cfg["SYSTEM_EMAIL_PROVIDER"]](cfg["SYSTEM_EMAIL_API_KEY"])
    try:
        sender.send(sender_email=cfg["SYSTEM_EMAIL_FROM"], sender_name=cfg.get("SYSTEM_EMAIL_FROM_NAME") or "ARC",
                    to_email=to_email, to_name=None, subject=subject, html=html, text=text, headers={},
                    reply_to=None, idempotency_key=uuid.uuid4().hex)
        return True
    except EmailProviderError as exc:
        # The link carries a secret token: log the failure, never the body.
        log.error("System email '%s' failed: %s", subject, exc)
        return False
