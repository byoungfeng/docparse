from __future__ import annotations

from pathlib import Path

from app.engines import EngineResult
from app.engines.office import parse_office
from app.engines.pdf import detect_pdf, parse_pdf
from app.ocr.base import OcrProvider

PDF_EXTENSIONS = {".pdf"}
OFFICE_EXTENSIONS = {
    ".doc",
    ".docx",
    ".docm",
    ".ppt",
    ".pps",
    ".pot",
    ".pptx",
    ".pptm",
    ".ppsx",
    ".ppsm",
    ".xls",
    ".xlsx",
    ".xlsm",
    ".xlsb",
    ".odt",
    ".ods",
    ".odp",
    ".rtf",
    ".epub",
    ".csv",
}


def _ext(filename: str) -> str:
    return Path(filename or "").suffix.lower()


def is_pdf(filename: str, content_type: str | None, data: bytes) -> bool:
    if data[:5] == b"%PDF-":
        return True
    if _ext(filename) in PDF_EXTENSIONS:
        return True
    if content_type and "pdf" in content_type.lower():
        return True
    return False


def parse_document(
    data: bytes,
    filename: str,
    content_type: str | None,
    ocr: OcrProvider,
) -> EngineResult:
    if is_pdf(filename, content_type, data):
        return parse_pdf(data, ocr)

    ext = _ext(filename)
    if ext in OFFICE_EXTENSIONS or ext == "":
        return parse_office(data, filename)

    # Unknown extension: try anydoc content sniff, else error via anydoc
    return parse_office(data, filename)


def detect_document(data: bytes, filename: str, content_type: str | None) -> EngineResult:
    if not is_pdf(filename, content_type, data):
        raise ValueError("Detect is only supported for PDF files")
    return detect_pdf(data)
