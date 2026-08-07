from fastapi.testclient import TestClient

from app.main import app


def test_index_page():
    client = TestClient(app)
    res = client.get("/")
    assert res.status_code == 200
    assert "text/html" in res.headers.get("content-type", "")
    assert "DocParse" in res.text
    assert "文档 → Markdown" in res.text


def test_static_js():
    client = TestClient(app)
    res = client.get("/static/app.js")
    assert res.status_code == 200
    assert "parseAsync" in res.text


def test_static_i18n():
    client = TestClient(app)
    res = client.get("/static/i18n.js")
    assert res.status_code == 200
    assert "zh-CN" in res.text
    assert '"en"' in res.text
