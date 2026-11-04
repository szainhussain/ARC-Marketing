"""Provider-neutral object storage + upload validation.

LocalStorage keeps files under UPLOAD_DIR with random keys (the original
filename is never used as a path). Production should swap in an S3/GCS
implementation of the same three methods.
"""

import hashlib
import os
import uuid

from flask import current_app

# extension -> (allowed content types, magic-byte prefixes or None for text)
ALLOWED = {
    "png": ({"image/png"}, [b"\x89PNG\r\n\x1a\n"]),
    "jpg": ({"image/jpeg"}, [b"\xff\xd8\xff"]),
    "jpeg": ({"image/jpeg"}, [b"\xff\xd8\xff"]),
    "gif": ({"image/gif"}, [b"GIF87a", b"GIF89a"]),
    "webp": ({"image/webp"}, [b"RIFF"]),
    "pdf": ({"application/pdf"}, [b"%PDF-"]),
    "txt": ({"text/plain"}, None),
    "md": ({"text/markdown", "text/plain"}, None),
    "csv": ({"text/csv", "text/plain", "application/vnd.ms-excel"}, None),
}


class UploadRejected(Exception):
    pass


def validate_upload(filename: str, content_type: str, data: bytes) -> str:
    """Returns a normalised extension or raises UploadRejected."""

    name = os.path.basename(filename or "").strip()
    if not name or "." not in name:
        raise UploadRejected("File must have an extension.")
    ext = name.rsplit(".", 1)[1].lower()
    if ext not in ALLOWED:
        raise UploadRejected(f"'.{ext}' files are not allowed. Allowed: {', '.join(sorted(ALLOWED))}.")
    max_bytes = current_app.config.get("MAX_UPLOAD_MB", 10) * 1024 * 1024
    if not data:
        raise UploadRejected("File is empty.")
    if len(data) > max_bytes:
        raise UploadRejected(f"File is larger than {current_app.config.get('MAX_UPLOAD_MB', 10)} MB.")
    types, magic = ALLOWED[ext]
    if content_type and content_type.split(";")[0].strip().lower() not in types | {"application/octet-stream"}:
        raise UploadRejected("File type does not match its extension.")
    if magic is not None:
        if not any(data.startswith(m) for m in magic):
            raise UploadRejected("File contents do not match its extension.")
        if ext == "webp" and data[8:12] != b"WEBP":
            raise UploadRejected("File contents do not match its extension.")
    else:
        try:
            data[:4096].decode("utf-8")
        except UnicodeDecodeError:
            raise UploadRejected("Text files must be UTF-8.")
    return ext


class LocalStorage:
    def __init__(self, root: str):
        self.root = os.path.abspath(root)

    def _path(self, key: str) -> str:
        path = os.path.abspath(os.path.join(self.root, key))
        if not path.startswith(self.root + os.sep):
            raise ValueError("Invalid storage key.")
        return path

    def put(self, organization_id: str, ext: str, data: bytes) -> tuple[str, str]:
        key = f"{organization_id}/{uuid.uuid4().hex}.{ext}"
        path = self._path(key)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as fh:
            fh.write(data)
        return key, hashlib.sha256(data).hexdigest()

    def get(self, key: str) -> bytes:
        with open(self._path(key), "rb") as fh:
            return fh.read()

    def delete(self, key: str) -> None:
        try:
            os.remove(self._path(key))
        except FileNotFoundError:
            pass


def get_storage() -> LocalStorage:
    return LocalStorage(current_app.config.get("UPLOAD_DIR", "storage/uploads"))
