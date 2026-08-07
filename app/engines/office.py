from __future__ import annotations

import anydoc

from app.engines import EngineResult


def _format_hint(filename: str, data: bytes) -> str | None:
    fmt = None
    if filename:
        try:
            fmt = anydoc.format_from_path(filename)
        except Exception:
            fmt = None
    if fmt is None:
        try:
            fmt = anydoc.format_from_bytes(data)
        except Exception:
            fmt = None

    if fmt is None:
        if filename.lower().endswith(".csv"):
            return "csv"
        return None

    if isinstance(fmt, str):
        return fmt
    for attr in ("name", "value"):
        if hasattr(fmt, attr):
            val = getattr(fmt, attr)
            if isinstance(val, str):
                return val.lower() if attr == "name" else val
    return str(fmt)


def parse_office(data: bytes, filename: str = "") -> EngineResult:
    """Convert office / epub / csv (and text PDFs via anydoc) to Markdown."""
    hint = _format_hint(filename, data)
    if hint:
        try:
            markdown = anydoc.to_markdown_bytes(data, hint)
        except Exception:
            markdown = anydoc.to_markdown_bytes(data)
    else:
        markdown = anydoc.to_markdown_bytes(data)

    return EngineResult(
        markdown=markdown or "",
        engine="anydoc",
        extra={"detected_format": hint},
    )
