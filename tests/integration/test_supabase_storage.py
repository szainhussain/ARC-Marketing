"""Supabase Storage backend: upload/download/delete go to a private bucket
over the REST API with the secret key, and an outage returns a clean 503.
No real network calls: urlopen is replaced with an in-memory fake."""

import io
import urllib.error

import pytest

from app import storage as storage_mod
from tests.conftest import create_org, register_and_login

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32
BASE = "https://proj.supabase.co"


class _Resp:
    def __init__(self, body=b""):
        self.body = body

    def read(self):
        return self.body

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


@pytest.fixture()
def fake_bucket(app, monkeypatch):
    app.config.update(STORAGE_BACKEND="supabase", SUPABASE_URL=BASE + "/",
                      SUPABASE_SECRET_KEY="sb_secret_test", SUPABASE_STORAGE_BUCKET="arc-uploads")
    objects, calls = {}, []

    def urlopen(req, timeout=None):
        calls.append(req)
        url, method = req.full_url, req.get_method()
        if method == "POST":
            objects[url.split("/object/", 1)[1]] = req.data
            return _Resp(b'{"Key":"ok"}')
        path = url.split("/object/", 1)[1].removeprefix("authenticated/")
        if path not in objects:
            raise urllib.error.HTTPError(url, 404, "not found", {}, None)
        if method == "GET":
            return _Resp(objects[path])
        del objects[path]
        return _Resp(b"{}")

    monkeypatch.setattr(storage_mod.urllib.request, "urlopen", urlopen)
    return objects, calls


def test_upload_download_delete_use_private_bucket(client, fake_bucket):
    objects, calls = fake_bucket
    register_and_login(client)
    org = create_org(client)
    url = f"/api/v1/organizations/{org['id']}/documents"
    resp = client.post(url, data={"file": (io.BytesIO(PNG), "logo.png", "image/png")},
                       content_type="multipart/form-data")
    assert resp.status_code == 201, resp.get_json()
    (key,) = objects
    assert key.startswith(f"arc-uploads/{org['id']}/") and key.endswith(".png")
    upload = calls[0]
    assert upload.full_url == f"{BASE}/storage/v1/object/{key}"
    assert upload.get_header("Apikey") == "sb_secret_test"
    assert upload.get_header("Authorization") is None  # new-style keys go only in apikey
    assert upload.get_header("Content-type") == "image/png"

    doc_id = resp.get_json()["document"]["id"]
    dl = client.get(f"{url}/{doc_id}/download")
    assert dl.status_code == 200 and dl.data == PNG
    assert "/object/authenticated/arc-uploads/" in calls[-1].full_url

    assert client.delete(f"{url}/{doc_id}").status_code == 200
    assert objects == {}


def test_storage_outage_returns_503_not_500(client, app, monkeypatch):
    app.config.update(STORAGE_BACKEND="supabase", SUPABASE_URL=BASE, SUPABASE_SECRET_KEY="sb_secret_test")

    def down(req, timeout=None):
        raise urllib.error.URLError("connection refused")

    monkeypatch.setattr(storage_mod.urllib.request, "urlopen", down)
    register_and_login(client)
    org = create_org(client)
    resp = client.post(f"/api/v1/organizations/{org['id']}/documents",
                       data={"file": (io.BytesIO(PNG), "logo.png", "image/png")},
                       content_type="multipart/form-data")
    assert resp.status_code == 503
    assert resp.get_json()["error"]["code"] == "SERVICE_UNAVAILABLE"
    # Nothing was recorded for a file that was never stored.
    assert client.get(f"/api/v1/organizations/{org['id']}/documents").get_json()["documents"] == []


def test_missing_config_and_bad_keys_are_rejected(app):
    with app.app_context():
        with pytest.raises(storage_mod.StorageUnavailable):
            storage_mod.SupabaseStorage("", "", "b")
        s = storage_mod.SupabaseStorage(BASE, "eyJlegacy.jwt.key", "arc-uploads")
        assert s.headers["Authorization"] == "Bearer eyJlegacy.jwt.key"  # legacy service_role JWT
        with pytest.raises(ValueError):
            s._url("../../other-bucket/secret.png")
