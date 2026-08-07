from __future__ import annotations

from fastapi import APIRouter, Depends, File, Header, HTTPException, UploadFile

from app import __version__
from app.api.schemas import (
    DetectResponse,
    HealthResponse,
    JobCreateResponse,
    JobStatusResponse,
    ParseMeta,
    ParseResponse,
)
from app.config import Settings, get_settings
from app.engines.router import detect_document, parse_document
from app.jobs.runner import enqueue_parse_job, get_job_store
from app.ocr.base import get_ocr_provider

router = APIRouter()


def require_api_key(
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    settings: Settings = Depends(get_settings),
) -> None:
    keys = settings.api_key_set
    if not keys:
        return
    if not x_api_key or x_api_key not in keys:
        raise HTTPException(status_code=401, detail="Invalid or missing X-API-Key")


async def _read_upload(file: UploadFile, settings: Settings) -> tuple[bytes, str, str | None]:
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty file")
    if len(data) > settings.max_upload_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds max size of {settings.max_upload_mb} MB",
        )
    return data, file.filename or "upload.bin", file.content_type


@router.get("/health", response_model=HealthResponse)
def health(settings: Settings = Depends(get_settings)) -> HealthResponse:
    engines = {
        "pdf-inspector": False,
        "anydoc": False,
        "ocr-rapid": False,
        "ocr-provider": settings.ocr_provider,
    }
    try:
        import pdf_inspector  # noqa: F401

        engines["pdf-inspector"] = True
    except Exception:
        pass
    try:
        import anydoc  # noqa: F401

        engines["anydoc"] = True
    except Exception:
        pass
    try:
        import rapidocr_onnxruntime  # noqa: F401
        import pypdfium2  # noqa: F401

        engines["ocr-rapid"] = True
    except Exception:
        pass
    return HealthResponse(status="ok", version=__version__, engines=engines)


@router.post("/v1/parse", response_model=ParseResponse, dependencies=[Depends(require_api_key)])
async def parse(
    file: UploadFile = File(...),
    settings: Settings = Depends(get_settings),
) -> ParseResponse:
    data, filename, content_type = await _read_upload(file, settings)
    try:
        ocr = get_ocr_provider(settings.ocr_provider)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    try:
        result = parse_document(data, filename, content_type, ocr)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return ParseResponse(
        markdown=result.markdown,
        meta=ParseMeta(
            filename=filename,
            content_type=content_type,
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
    )


@router.post("/v1/detect", response_model=DetectResponse, dependencies=[Depends(require_api_key)])
async def detect(
    file: UploadFile = File(...),
    settings: Settings = Depends(get_settings),
) -> DetectResponse:
    data, filename, content_type = await _read_upload(file, settings)
    try:
        result = detect_document(data, filename, content_type)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return DetectResponse(
        filename=filename,
        pdf_type=result.pdf_type or "unknown",
        confidence=result.confidence or 0.0,
        page_count=result.page_count or 0,
        pages_needing_ocr=result.pages_needing_ocr,
        processing_time_ms=result.processing_time_ms,
    )


@router.post(
    "/v1/parse/async",
    response_model=JobCreateResponse,
    dependencies=[Depends(require_api_key)],
)
async def parse_async(
    file: UploadFile = File(...),
    settings: Settings = Depends(get_settings),
) -> JobCreateResponse:
    data, filename, content_type = await _read_upload(file, settings)
    # Fail fast if OCR configured but missing deps
    if settings.ocr_provider.lower() in {"rapid", "rapidocr", "onnx"}:
        try:
            get_ocr_provider(settings.ocr_provider)
        except RuntimeError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc

    record = await enqueue_parse_job(
        data=data,
        filename=filename,
        content_type=content_type,
    )
    return JobCreateResponse(
        job_id=record.id,
        status=record.status,
        filename=record.filename,
        poll_url=f"/v1/jobs/{record.id}",
    )


@router.get(
    "/v1/jobs/{job_id}",
    response_model=JobStatusResponse,
    dependencies=[Depends(require_api_key)],
)
def get_job(job_id: str) -> JobStatusResponse:
    store = get_job_store()
    try:
        record = store.get(job_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Job not found") from exc

    result = None
    if record.result is not None:
        result = ParseResponse.model_validate(record.result)

    return JobStatusResponse(
        job_id=record.id,
        status=record.status,
        filename=record.filename,
        content_type=record.content_type,
        created_at=record.created_at,
        started_at=record.started_at,
        finished_at=record.finished_at,
        error=record.error,
        result=result,
    )
