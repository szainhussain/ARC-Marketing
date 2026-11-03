def test_live_endpoint(client):
    resp = client.get("/api/v1/health/live")
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "ok"


def test_ready_endpoint_checks_database(client):
    resp = client.get("/api/v1/health/ready")
    assert resp.status_code == 200
    assert resp.get_json()["database"] == "ok"
