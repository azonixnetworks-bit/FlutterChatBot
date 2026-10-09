from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ChunkDraft:
    content: str
    content_type: str
    page_number: int | None = None
    section_title: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class PageAwareChunker:
    """Small Phase 5/6 chunking seam; hybrid chunking arrives in Phase 12."""

    def __init__(self, max_chars: int = 1800) -> None:
        self._max_chars = max_chars

    def text_chunks(
        self, text: str, *, content_type: str, page_number: int | None = None,
        section_title: str | None = None, metadata: dict[str, Any] | None = None,
    ) -> list[ChunkDraft]:
        parts = [part.strip() for part in text.split("\n\n") if part.strip()]
        chunks: list[ChunkDraft] = []
        current = ""
        for part in parts:
            candidate = f"{current}\n\n{part}".strip()
            if current and len(candidate) > self._max_chars:
                chunks.append(ChunkDraft(current, content_type, page_number, section_title, metadata or {}))
                current = part
            else:
                current = candidate
        if current:
            chunks.append(ChunkDraft(current, content_type, page_number, section_title, metadata or {}))
        return chunks
