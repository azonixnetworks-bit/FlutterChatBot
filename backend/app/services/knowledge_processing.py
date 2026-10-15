from __future__ import annotations

import mimetypes

from app.services.chunking import ChunkDraft, PageAwareChunker
from app.services.pdf_ingestion import PdfExtractor, PdfIngestionError
from app.services.docx_ingestion import DocxExtractor
from app.services.spreadsheet_ingestion import SpreadsheetExtractor
from app.services.image_ingestion import ImageExtractor
from app.services.audio_ingestion import AudioExtractor
from app.services.supabase_data import SupabaseDataService


class KnowledgeProcessingService:
    def __init__(self, data: SupabaseDataService, pdf: PdfExtractor | None = None, docx: DocxExtractor | None = None) -> None:
        self._data = data
        self._pdf = pdf or PdfExtractor()
        self._chunker = PageAwareChunker()
        self._docx = docx or DocxExtractor()
        self._spreadsheet = SpreadsheetExtractor()
        self._image = ImageExtractor()
        self._audio = AudioExtractor()

    async def process(self, *, user_id: str, source_id: str, job_id: str) -> None:
        try:
            source = await self._data.get_owned_source(user_id=user_id, source_id=source_id)
            if source is None:
                raise PdfIngestionError("Knowledge source not found.")
            file_type = str(source.get("file_type", "")).lower()
            await self._data.update_progress(user_id=user_id, source_id=source_id, job_id=job_id, source_status="extracting", progress=5, step="Downloading private source")
            raw = await self._data.download_private_file(bucket=source["storage_bucket"], path=source["storage_path"])
            if file_type == "txt":
                await self._process_text(user_id, source_id, job_id, raw)
            elif file_type == "pdf":
                await self._process_pdf(user_id, source_id, job_id, source, raw)
            elif file_type == "docx":
                await self._process_docx(user_id, source_id, job_id, source, raw)
            elif file_type in {"csv", "xls", "xlsx"}:
                await self._process_spreadsheet(user_id, source_id, job_id, file_type, raw)
            elif file_type in {"jpg", "jpeg", "png", "webp"}:
                await self._process_image(user_id, source_id, job_id, source, raw)
            elif file_type in {"mp3", "wav", "m4a", "aac"}:
                await self._complete(user_id, source_id, job_id, self._audio.extract(raw, file_type=file_type, source_id=source_id))
            else:
                raise PdfIngestionError("This processing worker supports TXT, PDF, and DOCX sources only.")
        except Exception as exc:
            await self._data.fail_processing(user_id=user_id, source_id=source_id, job_id=job_id, message=str(exc) or "Processing failed.")
            raise

    async def _process_text(self, user_id: str, source_id: str, job_id: str, raw: bytes) -> None:
        text = raw.decode("utf-8", errors="replace").strip()
        if not text:
            raise PdfIngestionError("The text file is empty.")
        await self._data.update_progress(user_id=user_id, source_id=source_id, job_id=job_id, source_status="chunking", progress=70, step="Chunking text")
        chunks = self._chunker.text_chunks(text, content_type="text", metadata={"extraction_method": "utf8"})
        await self._complete(user_id, source_id, job_id, chunks)

    async def _process_pdf(self, user_id: str, source_id: str, job_id: str, source: dict, raw: bytes) -> None:
        await self._data.update_progress(user_id=user_id, source_id=source_id, job_id=job_id, source_status="extracting", progress=15, step="Opening PDF")
        extraction = self._pdf.extract(raw, source_id=source_id)
        await self._data.update_progress(user_id=user_id, source_id=source_id, job_id=job_id, source_status="analyzing", progress=60, step="Analyzing visuals and OCR")
        chunks = list(extraction.chunks)
        for index, asset in enumerate(extraction.visuals):
            asset_path = f"{user_id}/{source_id}/derived/page-{asset.page_number}-visual-{index}.{asset.extension}"
            await self._data.upload_private_file(bucket=source["storage_bucket"], path=asset_path, data=asset.image_bytes, content_type=mimetypes.guess_type(asset_path)[0] or "image/png")
            chunks.append(self._pdf.visual_chunk(asset, asset_path, source_id))
        await self._complete(user_id, source_id, job_id, chunks)

    async def _process_docx(self, user_id: str, source_id: str, job_id: str, source: dict, raw: bytes) -> None:
        extraction = self._docx.extract(raw, source_id=source_id)
        await self._data.update_progress(user_id=user_id, source_id=source_id, job_id=job_id, source_status="analyzing", progress=60, step="Analyzing DOCX visuals")
        chunks = list(extraction.chunks)
        for index, asset in enumerate(extraction.visuals):
            path = f"{user_id}/{source_id}/derived/docx-visual-{index}.{asset.extension}"
            await self._data.upload_private_file(bucket=source["storage_bucket"], path=path, data=asset.image_bytes, content_type=mimetypes.guess_type(path)[0] or "image/png")
            chunks.append(self._docx.visual_chunk(asset, path, source_id))
        await self._complete(user_id, source_id, job_id, chunks)

    async def _process_spreadsheet(self, user_id: str, source_id: str, job_id: str, file_type: str, raw: bytes) -> None:
        chunks = self._spreadsheet.extract(raw, file_type=file_type, source_id=source_id)
        if not chunks: raise PdfIngestionError("No usable rows were found in the spreadsheet.")
        await self._complete(user_id, source_id, job_id, chunks)

    async def _process_image(self, user_id: str, source_id: str, job_id: str, source: dict, raw: bytes) -> None:
        await self._data.update_progress(user_id=user_id, source_id=source_id, job_id=job_id, source_status="analyzing", progress=60, step="Running image OCR and vision")
        await self._complete(user_id, source_id, job_id, self._image.extract(raw, source_id=source_id, asset_path=source["storage_path"]))

    async def _complete(self, user_id: str, source_id: str, job_id: str, chunks: list[ChunkDraft]) -> None:
        await self._data.update_progress(user_id=user_id, source_id=source_id, job_id=job_id, source_status="chunking", progress=80, step="Preparing page-aware chunks")
        rows = [{"chunk_index": index, "content": chunk.content, "content_type": chunk.content_type, "page_number": chunk.page_number, "section_title": chunk.section_title, "start_time_ms": chunk.metadata.get("start_time_ms"), "end_time_ms": chunk.metadata.get("end_time_ms"), "metadata": chunk.metadata} for index, chunk in enumerate(chunks)]
        await self._data.replace_chunks_and_complete(user_id=user_id, source_id=source_id, job_id=job_id, chunks=rows)
