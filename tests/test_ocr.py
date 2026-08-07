from app.ocr.base import StubOcrProvider, get_ocr_provider


def test_stub_provider_mentions_pages():
    text = StubOcrProvider().ocr_pdf_pages(b"%PDF", [1, 2, 3])
    assert "1, 2, 3" in text
    assert "OCR stub" in text


def test_get_none_provider():
    p = get_ocr_provider("none")
    assert p.ocr_pdf_pages(b"%PDF", [1]) == ""
