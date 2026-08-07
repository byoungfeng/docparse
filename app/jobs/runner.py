from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
from typing import Optional

from app.api.schemas import ParseMeta, ParseResponse
from app.config import get_settings
from app.engines.router import parse_document
from app.jobs.store import JobRecord, JobStore
from app.ocr.base import get_ocr_provider


@lru_cache
def get_job_store() -> JobStore:
    settings = get_settings()
    return JobStore(settings.jobs_dir_path)


_executor: Optional[ThreadPoolExecutor] = None
_semaphore: Optional[asyncio.Semaphore] = None


def _get_executor() -> ThreadPoolExecutor:
    global _executor
    if _executor is None:
        settings = get_settings()
        _executor = ThreadPoolExecutor(
            max_workers=max(1, settings.job_workers),
            thread_name_prefix="docparse-job",
        )
    return _executor


def _get_semaphore() -> asyncio.Semaphore:
    global _semaphore
    if _semaphore is None:
        settings = get_settings()
        _semaphore = asyncio.Semaphore(max(1, settings.job_workers))
    return _semaphore


def _run_parse_job(job_id: str) -> None:
    settings = get_settings()
    store = get_job_store()
    store.mark_running(job_id)
    try:
        record = store.get(job_id)
        data = store.read_input(job_id)
        ocr = get_ocr_provider(settings.ocr_provider)
        result = parse_document(data, record.filename, record.content_type, ocr)
        payload = ParseResponse(
            markdown=result.markdown,
            meta=ParseMeta(
                filename=record.filename,
                content_type=record.content_type,
                engine=result.engine,  # type: ignore[arg-type]
                pdf_type=result.pdf_type,
                confidence=result.confidence,
                page_count=result.page_count,
                pages_needing_ocr=result.pages_needing_ocr,
                ocr_applied=result.ocr_applied,
                processing_time_ms=result.processing_time_ms,
                warnings=result.warnings,
                extra=result.extra,
            ),
        ).model_dump()
        store.mark_succeeded(job_id, payload)
    except Exception as exc:
        store.mark_failed(job_id, str(exc))


async def enqueue_parse_job(
    *,
    data: bytes,
    filename: str,
    content_type: str | None,
) -> JobRecord:
    store = get_job_store()
    record = store.create(data=data, filename=filename, content_type=content_type)
    asyncio.create_task(_execute_job(record.id))
    return record


async def _execute_job(job_id: str) -> None:
    sem = _get_semaphore()
    async with sem:
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(_get_executor(), _run_parse_job, job_id)
