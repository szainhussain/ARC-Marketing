"""Two-factor sign-in with an authenticator app (TOTP, RFC 6238) and
single-use recovery codes. Standard library only.

- 30-second steps, 6 digits, SHA-1 (what Google Authenticator, 1Password,
  Authy and Microsoft Authenticator expect), ±1 step for clock drift.
- A code can't be replayed: the last accepted step is stored.
- Recovery codes are shown once and stored only as hashes.
"""

import base64
import hashlib
import hmac
import json
import secrets
import struct
import time
import urllib.parse

from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db
from app.models.base import utcnow
from app.services.errors import ValidationError

ISSUER = "ARC"
STEP = 30
DIGITS = 6
RECOVERY_CODES = 8


def new_secret() -> str:
    return base64.b32encode(secrets.token_bytes(20)).decode().rstrip("=")


def _code_at(secret: str, step: int) -> str:
    key = base64.b32decode(secret + "=" * (-len(secret) % 8), casefold=True)
    digest = hmac.new(key, struct.pack(">Q", step), hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    value = struct.unpack(">I", digest[offset:offset + 4])[0] & 0x7FFFFFFF
    return str(value % 10 ** DIGITS).zfill(DIGITS)


def totp_now(secret: str, at: float | None = None) -> str:
    return _code_at(secret, int((at or time.time()) // STEP))


def matching_step(secret: str, code: str, at: float | None = None) -> int | None:
    code = "".join(ch for ch in (code or "") if ch.isdigit())
    if len(code) != DIGITS:
        return None
    now = int((at or time.time()) // STEP)
    for step in (now - 1, now, now + 1):
        if hmac.compare_digest(_code_at(secret, step), code):
            return step
    return None


def provisioning_uri(secret: str, email: str) -> str:
    label = urllib.parse.quote(f"{ISSUER}:{email}", safe=":@")
    return f"otpauth://totp/{label}?secret={secret}&issuer={ISSUER}&algorithm=SHA1&digits={DIGITS}&period={STEP}"


def _invalid(field: str, issue: str):
    raise ValidationError("Please correct the highlighted fields.", details=[{"field": field, "issue": issue}])


def start_setup(user) -> dict:
    if user.mfa_enabled_at:
        _invalid("code", "Two-factor sign-in is already on")
    user.mfa_pending_secret = new_secret()
    db.session.commit()
    return {"secret": user.mfa_pending_secret, "otpauth_uri": provisioning_uri(user.mfa_pending_secret, user.email)}


def _new_recovery_codes() -> tuple[list[str], str]:
    codes = [f"{secrets.token_hex(2)}-{secrets.token_hex(2)}-{secrets.token_hex(2)}" for _ in range(RECOVERY_CODES)]
    return codes, json.dumps([generate_password_hash(c) for c in codes])


def confirm_setup(user, code: str) -> list[str]:
    if not user.mfa_pending_secret:
        _invalid("code", "Start setup first")
    step = matching_step(user.mfa_pending_secret, code)
    if step is None:
        _invalid("code", "That code didn't match. Check your phone's time and try the newest code.")
    codes, hashed = _new_recovery_codes()
    user.mfa_secret, user.mfa_pending_secret = user.mfa_pending_secret, None
    user.mfa_last_step, user.mfa_recovery_hashes, user.mfa_enabled_at = step, hashed, utcnow()
    user.session_version = (user.session_version or 1) + 1  # sign out other sessions
    db.session.commit()
    return codes


def verify_second_factor(user, code: str | None, recovery_code: str | None) -> bool:
    """True if the code or an unused recovery code is valid (and consumes it)."""

    if code:
        step = matching_step(user.mfa_secret, code)
        if step is not None and step > (user.mfa_last_step or -1):
            user.mfa_last_step = step
            db.session.commit()
            return True
        return False
    if recovery_code:
        given = recovery_code.strip().lower()
        hashes = json.loads(user.mfa_recovery_hashes or "[]")
        for i, h in enumerate(hashes):
            if check_password_hash(h, given):
                hashes.pop(i)
                user.mfa_recovery_hashes = json.dumps(hashes)
                db.session.commit()
                return True
    return False


def disable(user, password: str, code: str | None, recovery_code: str | None) -> None:
    if not user.mfa_enabled_at:
        _invalid("code", "Two-factor sign-in is not on")
    if not user.check_password(password or ""):
        _invalid("password", "Incorrect password")
    if not verify_second_factor(user, code, recovery_code):
        _invalid("code", "That code didn't match")
    user.mfa_secret = user.mfa_pending_secret = user.mfa_recovery_hashes = None
    user.mfa_enabled_at, user.mfa_last_step = None, None
    db.session.commit()


def recovery_codes_left(user) -> int:
    return len(json.loads(user.mfa_recovery_hashes or "[]"))
