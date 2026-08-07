from __future__ import annotations

from typing import Protocol

from app.config import get_settings


class OcrProvider(Protocol):
    def ocr_pdf_pages(self, data: bytes, pages: list[int]) -> str:
        """OCR specific 1-indexed PDF pages; return Markdown fragment."""
        ...


class StubOcrProvider:
    """Placeholder when OCR extra is not installed / not selected."""

    def ocr_pdf_pages(self, data: bytes, pages: list[int]) -> str:
        listed = ", ".join(str(p) for p in pages) or "(none)"
        return (
            "\n\n> **OCR stub**: pages needing OCR were not processed: "
            f"{listed}. Install OCR extras and set `DOCPARSE_OCR_PROVIDER=rapid`.\n"
        )


class NoneOcrProvider:
    def ocr_pdf_pages(self, data: bytes, pages: list[int]) -> str:
        return ""


def get_ocr_provider(name: str | None = None) -> OcrProvider:
    settings = get_settings()
    key = (name or settings.ocr_provider or "stub").strip().lower()

    if key in {"none", "off", "disabled"}:
        return NoneOcrProvider()

    if key in {"rapid", "rapidocr", "onnx"}:
        try:
            from app.ocr.rapid import RapidOcrProvider
        except ImportError as exc:
            raise RuntimeError(
                "RapidOCR dependencies missing. Run: pip install -e \".[ocr]\""
            ) from exc
        return RapidOcrProvider(scale=settings.ocr_scale, max_pages=settings.ocr_max_pages)

    return StubOcrProvider()
