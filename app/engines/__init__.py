from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class EngineResult:
    markdown: str
    engine: str
    pdf_type: Optional[str] = None
    confidence: Optional[float] = None
    page_count: Optional[int] = None
    pages_needing_ocr: list[int] = field(default_factory=list)
    processing_time_ms: Optional[int] = None
    ocr_applied: bool = False
    warnings: list[str] = field(default_factory=list)
    extra: dict[str, Any] = field(default_factory=dict)
