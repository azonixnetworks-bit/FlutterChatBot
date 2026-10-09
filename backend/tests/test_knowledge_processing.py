from __future__ import annotations

import asyncio

import pytest

from app.services.knowledge_processing import KnowledgeProcessingService


class FakeData:
    def __init__(self, source: dict | None, raw: bytes = b"hello\n\nworld") -> None:
        self.source = source
        self.raw = raw
        self.replacements: list[list[dict]] = []
        self.failures: list[str] = []

    async def get_owned_source(self, **_: str): return self.source
    async def download_private_file(self, **_: str): return self.raw
    async def update_progress(self, **_: object): pass
    async def upload_private_file(self, **_: object): pass
    async def replace_chunks_and_complete(self, **kwargs: object): self.replacements.append(kwargs["chunks"])
    async def fail_processing(self, **kwargs: str): self.failures.append(kwargs["message"])


def test_reprocessing_replaces_instead_of_appending_chunks() -> None:
    data = FakeData({"file_type": "txt", "storage_bucket": "knowledge-files", "storage_path": "u/s/a.txt"})
    processor = KnowledgeProcessingService(data)  # type: ignore[arg-type]
    asyncio.run(processor.process(user_id="u", source_id="s", job_id="j"))
    asyncio.run(processor.process(user_id="u", source_id="s", job_id="j"))
    assert len(data.replacements) == 2
    assert len(data.replacements[0]) == len(data.replacements[1])


def test_owned_source_is_required_and_failure_is_recorded() -> None:
    data = FakeData(None)
    processor = KnowledgeProcessingService(data)  # type: ignore[arg-type]
    with pytest.raises(Exception, match="not found"):
        asyncio.run(processor.process(user_id="u", source_id="other-user-source", job_id="j"))
    assert data.failures


def test_processing_failure_marks_job_failed() -> None:
    data = FakeData({"file_type": "pdf", "storage_bucket": "knowledge-files", "storage_path": "u/s/a.pdf"}, b"broken")
    processor = KnowledgeProcessingService(data)  # type: ignore[arg-type]
    with pytest.raises(Exception):
        asyncio.run(processor.process(user_id="u", source_id="s", job_id="j"))
    assert data.failures
