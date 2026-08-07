from app.main import app


def test_health():
    from fastapi.testclient import TestClient

    client = TestClient(app)
    res = client.get("/health")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "ok"
    assert "engines" in body
