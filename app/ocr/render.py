from __future__ import annotations

from typing import Iterator

import pypdfium2 as pdfium
from PIL import Image


def render_pdf_pages(
    data: bytes,
    pages_1indexed: list[int],
    *,
    scale: float = 2.0,
) -> Iterator[tuple[int, Image.Image]]:
    """Yield (1-indexed page number, PIL image) for the given pages."""
    pdf = pdfium.PdfDocument(data)
    try:
        n = len(pdf)
        for page_no in pages_1indexed:
            if page_no < 1 or page_no > n:
                continue
            page = pdf[page_no - 1]
            bitmap = page.render(scale=scale)
            image = bitmap.to_pil()
            yield page_no, image
    finally:
        pdf.close()


def all_page_numbers(data: bytes) -> list[int]:
    pdf = pdfium.PdfDocument(data)
    try:
        return list(range(1, len(pdf) + 1))
    finally:
        pdf.close()
