from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from typing import Any, Callable, Protocol

import fitz

from app.services.chunking import ChunkDraft, PageAwareChunker


class PdfIngestionError(ValueError):
    pass


class VisionDescriber(Protocol):
    def describe(self, *, page_number: int, nearby_text: str, asset_path: str, kind: str) -> str: ...


class ContextualVisionDescriber:
    """Provider-independent baseline. A remote vision provider can replace this later."""

    def describe(self, *, page_number: int, nearby_text: str, asset_path: str, kind: str) -> str:
        context = " ".join(nearby_text.split())[:500]
        prefix = kind.replace("pdf_", "").replace("_", " ")
        return f"Page {page_number} {prefix}. Nearby document context: {context or 'No native text was available.'}"


@dataclass(frozen=True)
class VisualAsset:
    page_number: int
    image_bytes: bytes
    extension: str
    kind: str
    nearby_text: str


@dataclass(frozen=True)
class PdfExtraction:
    chunks: list[ChunkDraft]
    visuals: list[VisualAsset]


class PdfExtractor:
    def __init__(
        self,
        chunker: PageAwareChunker | None = None,
        vision: VisionDescriber | None = None,
        ocr: Callable[[bytes], str] | None = None,
    ) -> None:
        self._chunker = chunker or PageAwareChunker()
        self._vision = vision or ContextualVisionDescriber()
        self._ocr = ocr or self._default_ocr

    def extract(self, pdf_bytes: bytes, *, source_id: str) -> PdfExtraction:
        if not pdf_bytes:
            raise PdfIngestionError("The PDF is empty.")
        try:
            document = fitz.open(stream=pdf_bytes, filetype="pdf")
        except (fitz.FileDataError, RuntimeError) as exc:
            raise PdfIngestionError("The file is not a valid PDF or is corrupted.") from exc
        try:
            if document.needs_pass:
                raise PdfIngestionError("Password-protected PDFs are not supported.")
            if document.page_count == 0:
                raise PdfIngestionError("The PDF has no pages.")
            chunks: list[ChunkDraft] = []
            visuals: list[VisualAsset] = []
            for page_index in range(document.page_count):
                page = document.load_page(page_index)
                number = page_index + 1
                text = page.get_text("text").strip()
                heading = self._heading(text)
                base_metadata = {"extraction_method": "pymupdf", "source_id": source_id}
                if text:
                    chunks.extend(self._chunker.text_chunks(text, content_type="pdf_text", page_number=number, section_title=heading, metadata=base_metadata))
                if len(text) < 40:
                    rendered = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False).tobytes("png")
                    ocr_text = self._ocr(rendered).strip()
                    if ocr_text and self._meaningfully_different(text, ocr_text):
                        chunks.extend(self._chunker.text_chunks(ocr_text, content_type="pdf_ocr", page_number=number, section_title=heading, metadata={**base_metadata, "extraction_method": "ocr"}))
                tables = self._tables(page)
                for table_index, table in enumerate(tables):
                    readable = self._table_text(table)
                    if readable:
                        chunks.append(ChunkDraft(readable, "pdf_table", number, heading, {**base_metadata, "table_index": table_index, "row_count": len(table)}))
                nearby = text or ""
                for image_index, image in enumerate(page.get_images(full=True)):
                    extracted = document.extract_image(image[0])
                    image_bytes = extracted.get("image", b"")
                    if len(image_bytes) < 2048:
                        continue
                    extension = extracted.get("ext", "png")
                    visuals.append(VisualAsset(number, image_bytes, extension, self._visual_kind(nearby, default="pdf_image"), nearby))
                if page.get_drawings() and len(text) < 400:
                    rendered = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5), alpha=False).tobytes("png")
                    visuals.append(VisualAsset(number, rendered, "png", self._visual_kind(nearby, default="pdf_diagram"), nearby))
            if not chunks and not visuals:
                raise PdfIngestionError("No usable text or visual content was found in the PDF.")
            return PdfExtraction(chunks, visuals)
        finally:
            document.close()

    def visual_chunk(self, asset: VisualAsset, asset_path: str, source_id: str) -> ChunkDraft:
        return ChunkDraft(self._vision.describe(page_number=asset.page_number, nearby_text=asset.nearby_text, asset_path=asset_path, kind=asset.kind), asset.kind, asset.page_number, self._heading(asset.nearby_text), {"source_id": source_id, "asset_path": asset_path, "extraction_method": "pymupdf", "nearby_text": asset.nearby_text[:500]})

    @staticmethod
    def _heading(text: str) -> str | None:
        for line in text.splitlines()[:6]:
            line = line.strip()
            if 3 <= len(line) <= 160 and (line.isupper() or len(line.split()) <= 12):
                return line
        return None

    @staticmethod
    def _meaningfully_different(native: str, ocr: str) -> bool:
        return len(ocr) > max(30, len(native) * 2)

    @staticmethod
    def _visual_kind(nearby_text: str, *, default: str) -> str:
        context = nearby_text.lower()
        if "chart" in context or "graph" in context:
            return "pdf_chart"
        if "diagram" in context or "figure" in context:
            return "pdf_diagram"
        if "screenshot" in context or "screen shot" in context:
            return "pdf_image"
        return default

    @staticmethod
    def _tables(page: fitz.Page) -> list[list[list[str]]]:
        try:
            finder = page.find_tables()
            return [table.extract() for table in finder.tables]
        except (AttributeError, RuntimeError):
            return []

    @staticmethod
    def _table_text(rows: list[list[str]]) -> str:
        if not rows:
            return ""
        header = [str(cell or "").strip() for cell in rows[0]]
        lines = ["Table: " + " | ".join(header)]
        for row_number, row in enumerate(rows[1:], start=1):
            values = [str(cell or "").strip() for cell in row]
            if any(values):
                pairs = [f"{header[index] or f'Column {index + 1}'}: {value}" for index, value in enumerate(values) if value]
                lines.append(f"Row {row_number}: " + "; ".join(pairs))
        return "\n".join(lines) if len(lines) > 1 else ""

    @staticmethod
    def _default_ocr(png_bytes: bytes) -> str:
        try:
            from PIL import Image
            import pytesseract
            return pytesseract.image_to_string(Image.open(BytesIO(png_bytes)))
        except Exception:
            return ""
