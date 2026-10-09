from __future__ import annotations

import fitz
import pytest

from app.services.pdf_ingestion import PdfExtractor, PdfIngestionError


def _pdf(*pages: str) -> bytes:
    document = fitz.open()
    for text in pages:
        page = document.new_page()
        if text:
            page.insert_text((72, 72), text)
    data = document.tobytes()
    document.close()
    return data


def test_extracts_normal_text_with_page_metadata() -> None:
    result = PdfExtractor(ocr=lambda _: "").extract(_pdf("INTRODUCTION\n\nThis is native PDF text."), source_id="source")
    assert result.chunks[0].content_type == "pdf_text"
    assert result.chunks[0].page_number == 1
    assert result.chunks[0].section_title == "INTRODUCTION"


def test_extracts_each_page_independently() -> None:
    result = PdfExtractor(ocr=lambda _: "").extract(_pdf("First page native text.", "Second page native text."), source_id="source")
    assert {chunk.page_number for chunk in result.chunks} == {1, 2}


def test_low_text_page_uses_ocr_without_native_duplicate() -> None:
    result = PdfExtractor(ocr=lambda _: "OCR recovered content from a scanned page.").extract(_pdf(""), source_id="source")
    assert len(result.chunks) == 1
    assert result.chunks[0].content_type == "pdf_ocr"
    assert result.chunks[0].page_number == 1


def test_table_representation_preserves_headers_and_rows() -> None:
    readable = PdfExtractor._table_text([["Item", "Value"], ["Revenue", "$20"], ["Cost", "$10"]])
    assert "Item | Value" in readable
    assert "Row 1: Item: Revenue; Value: $20" in readable


def test_visual_chunk_keeps_private_asset_reference_and_context() -> None:
    extractor = PdfExtractor(ocr=lambda _: "")
    from app.services.pdf_ingestion import VisualAsset
    asset = VisualAsset(2, b"image", "png", "pdf_chart", "See chart below for a demand zone")
    chunk = extractor.visual_chunk(asset, "user/source/derived/page-2.png", "source")
    assert chunk.content_type == "pdf_chart"
    assert chunk.metadata["asset_path"].startswith("user/source/")
    assert "demand zone" in chunk.content


def test_visual_kind_uses_nearby_caption_context() -> None:
    assert PdfExtractor._visual_kind("See the graph below", default="pdf_image") == "pdf_chart"
    assert PdfExtractor._visual_kind("Figure 3: architecture diagram", default="pdf_image") == "pdf_diagram"


@pytest.mark.parametrize("data", [b"", b"not a pdf"])
def test_rejects_empty_or_corrupted_pdf(data: bytes) -> None:
    with pytest.raises(PdfIngestionError):
        PdfExtractor().extract(data, source_id="source")


def test_rejects_password_protected_pdf() -> None:
    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), "Private PDF")
    protected = document.tobytes(encryption=fitz.PDF_ENCRYPT_AES_256, owner_pw="owner", user_pw="user")
    document.close()
    with pytest.raises(PdfIngestionError, match="Password"):
        PdfExtractor().extract(protected, source_id="source")
