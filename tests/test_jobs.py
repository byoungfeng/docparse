import time

from app.config import get_settings
from app.jobs.runner import get_job_store
from app.main import app


def test_async_parse_csv(tmp_path, monkeypatch):
    monkeypatch.setenv("DOCPARSE_JOBS_DIR", str(tmp_path / "jobs"))
    monkeypatch.setenv("DOCPARSE_OCR_PROVIDER", "none")
    get_settings.cache_clear()
    get_job_store.cache_clear()

    from fastapi.testclient import TestClient

    with TestClient(app) as client:
        res = client.post(
            "/v1/parse/async",
            files={"file": ("demo.csv", b"name,age\nAda,36\n", "text/csv")},
        )
        assert res.status_code == 200, res.text
        body = res.json()
        job_id = body["job_id"]
        assert body["status"] == "queued"
        assert body["poll_url"] == f"/v1/jobs/{job_id}"

        final = None
        for _ in range(50):
            poll = client.get(f"/v1/jobs/{job_id}")
            assert poll.status_code == 200
            final = poll.json()
            if final["status"] in {"succeeded", "failed"}:
                break
            time.sleep(0.1)

        assert final is not None
        assert final["status"] == "succeeded", final
        assert final["result"]["markdown"]
        assert "Ada" in final["result"]["markdown"] or "age" in final["result"]["markdown"]
