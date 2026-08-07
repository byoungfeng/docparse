from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class ParseMeta(BaseModel):
    filename: str
    content_type: Optional[str] = None
    engine: Literal["pdf-inspector", "anydoc", "ocr", "mixed"]
    pdf_type: Optional[str] = None
    confidence: Optional[float] = None
    page_count: Optional[int] = None
    pages_needing_ocr: list[int] = Field(default_factory=list)
    ocr_applied: bool = False
    processing_time_ms: Optional[int] = None
    warnings: list[str] = Field(default_factory=list)
    extra: dict[str, Any] = Field(default_factory=dict)


class ParseResponse(BaseModel):
    markdown: str
    meta: ParseMeta


class DetectResponse(BaseModel):
    filename: str
    pdf_type: str
    confidence: float
    page_count: int
    pages_needing_ocr: list[int]
    processing_time_ms: Optional[int] = None


class JobCreateResponse(BaseModel):
    job_id: str
    status: Literal["queued", "running", "succeeded", "failed"]
    filename: str
    poll_url: str


class JobStatusResponse(BaseModel):
    job_id: str
    status: Literal["queued", "running", "succeeded", "failed"]
    filename: str
    content_type: Optional[str] = None
    created_at: str
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    error: Optional[str] = None
    result: Optional[ParseResponse] = None


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str
    engines: dict[str, Any]
