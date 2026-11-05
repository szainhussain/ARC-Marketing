"""Client-owned email senders for outreach (docs/DECISIONS.md D18). Each
workspace connects its own Brevo or Resend account, so emails go out from
the client's domain and reputation.

Brevo:  POST https://api.brevo.com/v3/smtp/email   (header api-key)
        GET  https://api.brevo.com/v3/account      (key check)
        https://developers.brevo.com/reference/sendtransacemail
Resend: POST https://api.resend.com/emails          (Bearer; Idempotency-Key supported)
        https://resend.com/docs/api-reference/emails/send-email"""

import json
import urllib.error
import urllib.request

TIMEOUT = 20


class EmailProviderError(Exception):
    def __init__(self, message: str, status: int | None = None, retryable: bool = False):
        super().__init__(message)
        self.status, self.retryable = status, retryable


def _http(method: str, url: str, headers: dict, body: dict | None = None) -> dict:
    """The only network call in this module (patched in tests)."""
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    for k, v in {"Accept": "application/json", "User-Agent": "ARC-Outreach/1", **headers}.items():
        req.add_header(k, v)
    if data is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:  # noqa: S310 - fixed provider hosts
            raw = resp.read().decode()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        msg = ""
        try:
            j = json.loads(exc.read().decode())
            msg = j.get("message") or j.get("name") or ""
        except Exception:  # noqa: BLE001
            pass
        raise EmailProviderError(f"Email provider returned {exc.code}{': ' + msg if msg else ''}", status=exc.code,
                                 retryable=exc.code in (408, 429) or exc.code >= 500) from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise EmailProviderError(f"Could not reach the email provider ({type(exc).__name__})", retryable=True) from exc


class BrevoSender:
    name = "brevo"
    retry_safe = False  # no idempotency key: never resend after an uncertain attempt

    def __init__(self, api_key: str):
        self.key = api_key

    def check(self) -> dict:
        info = _http("GET", "https://api.brevo.com/v3/account", {"api-key": self.key})
        return {"account": info.get("email") or info.get("companyName") or "Brevo account"}

    def send(self, *, sender_email, sender_name, to_email, to_name, subject, html, text, headers, reply_to, idempotency_key):
        body = {"sender": {"email": sender_email, "name": sender_name}, "to": [{"email": to_email, **({"name": to_name} if to_name else {})}],
                "subject": subject, "htmlContent": html, "textContent": text, "headers": headers}
        if reply_to:
            body["replyTo"] = {"email": reply_to}
        r = _http("POST", "https://api.brevo.com/v3/smtp/email", {"api-key": self.key}, body)
        return r.get("messageId") or ""


class ResendSender:
    name = "resend"
    retry_safe = True

    def __init__(self, api_key: str):
        self.key = api_key

    def check(self) -> dict:
        try:
            _http("GET", "https://api.resend.com/domains", {"Authorization": f"Bearer {self.key}"})
        except EmailProviderError as exc:
            # A "sending access" key cannot list domains but can still send.
            if exc.status not in (401, 403) or "restricted" not in str(exc).lower():
                raise
        return {"account": "Resend account"}

    def send(self, *, sender_email, sender_name, to_email, to_name, subject, html, text, headers, reply_to, idempotency_key):
        body = {"from": f"{sender_name} <{sender_email}>", "to": [to_email], "subject": subject, "html": html,
                "text": text, "headers": headers}
        if reply_to:
            body["reply_to"] = reply_to
        r = _http("POST", "https://api.resend.com/emails",
                  {"Authorization": f"Bearer {self.key}", "Idempotency-Key": idempotency_key}, body)
        return r.get("id") or ""


PROVIDERS = {"brevo": BrevoSender, "resend": ResendSender}
