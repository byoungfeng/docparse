from __future__ import annotations

import pdf_inspector

from app.engines import EngineResult
from app.ocr.base import OcrProvider
from app.ocr.render import all_page_numbers


def detect_pdf(data: bytes) -> EngineResult:
    result = pdf_inspector.detect_pdf_bytes(data)
    return EngineResult(
        markdown="",
        engine="pdf-inspector",
        pdf_type=result.pdf_type,
        confidence=float(result.confidence),
        page_count=int(result.page_count),
        pages_needing_ocr=list(result.pages_needing_ocr or []),
        processing_time_ms=getattr(result, "processing_time_ms", None),
    )


def _pages_for_ocr(result, data: bytes) -> list[int]:
    pages = list(result.pages_needing_ocr or [])
    pdf_type = (result.pdf_type or "").lower()
    markdown = (result.markdown or "").strip()

    # Fully scanned / image PDFs may report empty markdown; OCR all pages.
    if not pages and pdf_type in {"scanned", "image_based"} and not markdown:
        return all_page_numbers(data)

    # Encoding-broken text PDFs: if almost empty, OCR flagged pages or all.
    if getattr(result, "has_encoding_issues", False) and len(markdown) < 40:
        return pages or all_page_numbers(data)

    return pages


def parse_pdf(data: bytes, ocr: OcrProvider) -> EngineResult:
    result = pdf_inspector.process_pdf_bytes(data)
    markdown = result.markdown or ""
    pages_needing_ocr = _pages_for_ocr(result, data)
    warnings: list[str] = []
    ocr_applied = False

    if getattr(result, "has_encoding_issues", False):
        warnings.append("PDF has encoding issues; OCR fallback may improve quality.")

    if pages_needing_ocr:
        fragment = ocr.ocr_pdf_pages(data, pages_needing_ocr)
        if fragment.strip():
            markdown = (markdown.rstrip() + "\n\n" + fragment).strip() + "\n"
            if "OCR stub" in fragment:
                warnings.append(f"Pages needing OCR (not processed): {pages_needing_ocr}")
            else:
                ocr_applied = True
                warnings.append(f"OCR applied to pages: {pages_needing_ocr[:20]}"
                                + ("..." if len(pages_needing_ocr) > 20 else ""))
        else:
            warnings.append(f"Pages needing OCR (skipped): {pages_needing_ocr}")

    return EngineResult(
        markdown=markdown,
        engine="mixed" if ocr_applied else "pdf-inspector",
        pdf_type=result.pdf_type,
        confidence=float(result.confidence) if result.confidence is not None else None,
        page_count=int(result.page_count),
        pages_needing_ocr=pages_needing_ocr,
        processing_time_ms=getattr(result, "processing_time_ms", None),
        ocr_applied=ocr_applied,
        warnings=warnings,
        extra={
            "is_complex_layout": bool(getattr(result, "is_complex_layout", False)),
            "pages_with_tables": list(getattr(result, "pages_with_tables", []) or []),
            "title": getattr(result, "title", None),
        },
    )
