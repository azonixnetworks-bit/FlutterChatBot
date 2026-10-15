from io import BytesIO
from typing import Protocol
from PIL import Image
from app.services.chunking import ChunkDraft
from app.services.pdf_ingestion import ContextualVisionDescriber

class ImageIngestionError(ValueError): pass
class OcrProvider(Protocol):
    def extract(self, data: bytes) -> tuple[str, dict]: ...
class VisionProvider(Protocol):
    def describe(self, data: bytes) -> tuple[str, str]: ...
class ImageExtractor:
    def __init__(self, ocr=None, vision: VisionProvider | None = None, max_pixels: int = 40_000_000) -> None:
        self._ocr = ocr; self._vision = vision; self._max_pixels=max_pixels
    def extract(self, data: bytes, *, source_id: str, asset_path: str) -> list[ChunkDraft]:
        try:
            image=Image.open(BytesIO(data)); image.verify(); image=Image.open(BytesIO(data))
        except Exception as exc: raise ImageIngestionError("The file is not a valid image.") from exc
        if image.width * image.height > self._max_pixels: raise ImageIngestionError("Image exceeds the configured pixel limit.")
        meta={"source_id":source_id,"asset_path":asset_path,"width":image.width,"height":image.height,"format":image.format,"file_size_bytes":len(data)}
        chunks=[]
        if self._ocr:
            text, details=self._ocr.extract(data) if hasattr(self._ocr,"extract") else (self._ocr(data), {})
            if text.strip(): chunks.append(ChunkDraft(text.strip(),"image_ocr",metadata={**meta,"extraction_method":"ocr","ocr":details}))
        if self._vision:
            description, kind=self._vision.describe(data)
            if description.strip(): chunks.append(ChunkDraft(description.strip(),kind,metadata={**meta,"extraction_method":"vision"}))
        return chunks
