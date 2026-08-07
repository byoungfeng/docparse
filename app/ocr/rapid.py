from __future__ import annotations

from functools import lru_cache

import numpy as np

from app.ocr.render import render_pdf_pages


@lru_cache(maxsize=1)
def _engine():
    from rapidocr_onnxruntime import RapidOCR

    return RapidOCR()


class RapidOcrProvider:
    """Local OCR via RapidOCR (ONNX) + pypdfium2 page render."""

    def __init__(self, *, scale: float = 2.0, max_pages: int = 50) -> None:
        self.scale = scale
        self.max_pages = max_pages

    def ocr_pdf_pages(self, data: bytes, pages: list[int]) -> str:
        if not pages:
            return ""

        limited = pages[: self.max_pages]
        truncated = len(pages) > self.max_pages
        engine = _engine()
        parts: list[str] = []

        for page_no, image in render_pdf_pages(data, limited, scale=self.scale):
            arr = np.asarray(image.convert("RGB"))
            result, _ = engine(arr)
            lines: list[str] = []
            if result:
                for item in result:
                    # item: [box, text, score]
                    if len(item) >= 2 and item[1]:
                        lines.append(str(item[1]).strip())
            body = "\n".join(line for line in lines if line)
            parts.append(f"## Page {page_no}\n\n{body}".rstrip() + "\n")

        if truncated:
            parts.append(
                f"\n> OCR truncated: processed {len(limited)}/{len(pages)} pages "
                f"(limit DOCPARSE_OCR_MAX_PAGES={self.max_pages}).\n"
            )

        return "\n".join(parts).strip() + ("\n" if parts else "")
