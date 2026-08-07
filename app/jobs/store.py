from __future__ import annotations

import json
import threading
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal, Optional

JobStatus = Literal["queued", "running", "succeeded", "failed"]


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class JobRecord:
    id: str
    status: JobStatus
    filename: str
    content_type: Optional[str] = None
    created_at: str = field(default_factory=_utc_now)
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    error: Optional[str] = None
    result: Optional[dict[str, Any]] = None

    def to_public(self) -> dict[str, Any]:
        data = asdict(self)
        return data


class JobStore:
    """Filesystem job store: data/jobs/<id>/{meta.json,input.bin,result.json}."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def _dir(self, job_id: str) -> Path:
        return self.root / job_id

    def create(
        self,
        *,
        data: bytes,
        filename: str,
        content_type: str | None,
    ) -> JobRecord:
        job_id = uuid.uuid4().hex
        job_dir = self._dir(job_id)
        job_dir.mkdir(parents=True, exist_ok=False)
        (job_dir / "input.bin").write_bytes(data)
        record = JobRecord(
            id=job_id,
            status="queued",
            filename=filename,
            content_type=content_type,
        )
        self._write_meta(record)
        return record

    def _write_meta(self, record: JobRecord) -> None:
        path = self._dir(record.id) / "meta.json"
        payload = asdict(record)
        # result stored separately when large
        payload.pop("result", None)
        text = json.dumps(payload, ensure_ascii=False, indent=2)
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(text, encoding="utf-8")
        tmp.replace(path)

    def _read_meta(self, job_id: str) -> JobRecord:
        path = self._dir(job_id) / "meta.json"
        if not path.exists():
            raise KeyError(job_id)
        # Retry briefly if another thread is mid-write
        raw_text = ""
        for _ in range(10):
            raw_text = path.read_text(encoding="utf-8")
            if raw_text.strip():
                break
            time.sleep(0.01)
        if not raw_text.strip():
            raise KeyError(job_id)
        raw = json.loads(raw_text)
        result_path = self._dir(job_id) / "result.json"
        result = None
        if result_path.exists():
            result_text = result_path.read_text(encoding="utf-8")
            if result_text.strip():
                result = json.loads(result_text)
        return JobRecord(
            id=raw["id"],
            status=raw["status"],
            filename=raw["filename"],
            content_type=raw.get("content_type"),
            created_at=raw.get("created_at") or _utc_now(),
            started_at=raw.get("started_at"),
            finished_at=raw.get("finished_at"),
            error=raw.get("error"),
            result=result,
        )

    def get(self, job_id: str) -> JobRecord:
        return self._read_meta(job_id)

    def read_input(self, job_id: str) -> bytes:
        path = self._dir(job_id) / "input.bin"
        if not path.exists():
            raise KeyError(job_id)
        return path.read_bytes()

    def mark_running(self, job_id: str) -> JobRecord:
        with self._lock:
            record = self._read_meta(job_id)
            record.status = "running"
            record.started_at = _utc_now()
            record.error = None
            self._write_meta(record)
            return record

    def mark_succeeded(self, job_id: str, result: dict[str, Any]) -> JobRecord:
        with self._lock:
            record = self._read_meta(job_id)
            record.status = "succeeded"
            record.finished_at = _utc_now()
            record.error = None
            record.result = result
            self._write_meta(record)
            result_path = self._dir(job_id) / "result.json"
            tmp = result_path.with_suffix(".json.tmp")
            tmp.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
            tmp.replace(result_path)
            return record

    def mark_failed(self, job_id: str, error: str) -> JobRecord:
        with self._lock:
            record = self._read_meta(job_id)
            record.status = "failed"
            record.finished_at = _utc_now()
            record.error = error
            self._write_meta(record)
            return record

    def fail_orphaned_running(self) -> int:
        """Mark jobs left in running state after a crash/restart."""
        count = 0
        for child in self.root.iterdir():
            if not child.is_dir():
                continue
            meta = child / "meta.json"
            if not meta.exists():
                continue
            try:
                record = self._read_meta(child.name)
            except Exception:
                continue
            if record.status == "running":
                self.mark_failed(record.id, "Interrupted by server restart")
                count += 1
        return count
