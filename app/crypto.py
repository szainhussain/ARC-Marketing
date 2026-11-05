"""Encryption at rest for third-party credentials (e.g. a WordPress.com
access token). Tokens are only ever decrypted inside the worker or the
service that calls the provider; they are never returned by the API.

The key is derived from INTEGRATION_ENCRYPTION_KEY (any long random value). If it is not
set, one is derived from SECRET_KEY so local development works; production
should set its own key, because rotating SECRET_KEY would otherwise make
stored tokens unreadable (clients would simply reconnect)."""

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken
from flask import current_app


def _fernet() -> Fernet:
    # Any long random string works (e.g. Render's "Generate" value): it is
    # hashed into a valid 32-byte Fernet key.
    material = current_app.config.get("INTEGRATION_ENCRYPTION_KEY") or current_app.config["SECRET_KEY"]
    digest = hashlib.sha256(("arc-integrations:" + material).encode()).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt_secret(plaintext: str) -> str:
    return _fernet().encrypt(plaintext.encode()).decode()


def decrypt_secret(ciphertext: str) -> str | None:
    try:
        return _fernet().decrypt(ciphertext.encode()).decode()
    except (InvalidToken, ValueError):
        return None
