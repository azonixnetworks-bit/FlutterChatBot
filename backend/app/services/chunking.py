"""Shared deterministic hybrid chunk planning; no embedding dependency."""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field, replace
from typing import Any, Protocol, Sequence


@dataclass(frozen=True)
class ChunkDraft:
    content: str
    content_type: str
    page_number: int | None = None
    section_title: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ChunkingPolicy:
    target_tokens: int = 650
    max_tokens: int = 800
    min_tokens: int = 80
    overlap_tokens: int = 80
    parent_target_tokens: int = 1400
    parent_max_tokens: int = 1800
    semantic_enabled: bool = True
    multimodal_context_window_ms: int = 30_000
    table_rows_per_group: int = 25

    def __post_init__(self) -> None:
        if not (1 <= self.min_tokens <= self.target_tokens <= self.max_tokens):
            raise ValueError("Chunk token limits must satisfy min <= target <= max.")
        if not (0 <= self.overlap_tokens < self.max_tokens):
            raise ValueError("Chunk overlap must be non-negative and below the maximum.")
        if not (self.target_tokens <= self.parent_target_tokens <= self.parent_max_tokens):
            raise ValueError("Parent limits must satisfy target <= parent target <= parent max.")
        if self.table_rows_per_group < 1 or self.multimodal_context_window_ms < 0:
            raise ValueError("Chunking group limits must be positive.")


class TokenCounter(Protocol):
    """Provider-independent. The built-in fallback is explicitly estimated."""
    is_exact: bool
    def count(self, text: str) -> int: ...
    def split(self, text: str, limit: int) -> list[str]: ...


class WhitespaceTokenCounter:
    is_exact = False
    def count(self, text: str) -> int: return len(re.findall(r"\S+", text))
    def split(self, text: str, limit: int) -> list[str]:
        words = re.findall(r"\S+", text)
        return [" ".join(words[start:start + limit]) for start in range(0, len(words), limit)]


class SemanticBoundaryDetector(Protocol):
    """Optional seam for an in-memory semantic model in a later phase."""
    def is_boundary(self, previous: str, current: str) -> bool: ...


class DeterministicBoundaryDetector:
    def is_boundary(self, previous: str, current: str) -> bool:
        old = {word.lower() for word in re.findall(r"[A-Za-z0-9]{4,}", previous)}
        new = {word.lower() for word in re.findall(r"[A-Za-z0-9]{4,}", current)}
        return bool(old and new and len(old & new) / min(len(old), len(new)) < 0.04)


@dataclass(frozen=True)
class ChunkingBlock:
    content: str
    content_type: str
    position: int
    page_number: int | None = None
    section_title: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_draft(cls, draft: ChunkDraft, position: int) -> "ChunkingBlock":
        return cls(draft.content, draft.content_type, position, draft.page_number, draft.section_title, dict(draft.metadata))


@dataclass(frozen=True)
class ChunkingDocument:
    source_id: str | None
    blocks: Sequence[ChunkingBlock]


@dataclass(frozen=True)
class ChunkCandidate:
    block: ChunkingBlock
    content: str
    token_count: int
    semantic_split: bool = False


@dataclass(frozen=True)
class ChunkMetadata:
    chunk_role: str
    block_start: int
    block_end: int
    token_count: int
    semantic_split: bool
    overlap_tokens: int
    multimodal: bool
    def as_dict(self) -> dict[str, Any]:
        return {"chunk_role": self.chunk_role, "block_start": self.block_start, "block_end": self.block_end,
                "token_count": self.token_count, "token_count_estimated": True, "chunking_strategy": "hybrid_structural",
                "semantic_split": self.semantic_split, "overlap_tokens": self.overlap_tokens, "multimodal": self.multimodal}


@dataclass(frozen=True)
class ChunkResult:
    chunks: list[ChunkDraft]
    parent_count: int
    child_count: int
    duplicates_skipped: int


class HybridChunkingEngine:
    """Structural-first chunk planner with token-safe deterministic fallbacks."""
    _ATOMIC_TYPES = ("table", "image", "chart", "diagram", "visual", "frame")

    def __init__(self, policy: ChunkingPolicy | None = None, token_counter: TokenCounter | None = None,
                 boundary_detector: SemanticBoundaryDetector | None = None) -> None:
        self.policy = policy or ChunkingPolicy()
        self._tokens = token_counter or WhitespaceTokenCounter()
        self._boundary_detector = boundary_detector or DeterministicBoundaryDetector()

    def plan(self, document: ChunkingDocument) -> ChunkResult:
        blocks = [b for b in document.blocks if b.content and b.content.strip()]
        chunks: list[ChunkDraft] = []
        seen: set[str] = set()
        duplicates = 0
        index = 0
        while index < len(blocks):
            group, index = self._next_group(blocks, index)
            planned, skipped = self._plan_group(group, seen, len(chunks))
            chunks.extend(planned)
            duplicates += skipped
        return ChunkResult(chunks, sum(c.metadata.get("chunk_role") == "parent" for c in chunks),
                           sum(c.metadata.get("chunk_role") == "child" for c in chunks), duplicates)

    def _next_group(self, blocks: list[ChunkingBlock], index: int) -> tuple[list[ChunkingBlock], int]:
        first = blocks[index]
        if self._is_atomic(first): return [first], index + 1
        key, group = self._structural_key(first), [first]
        index += 1
        while index < len(blocks) and not self._is_atomic(blocks[index]) and self._structural_key(blocks[index]) == key:
            group.append(blocks[index]); index += 1
        return group, index

    def _plan_group(self, blocks: list[ChunkingBlock], seen: set[str], global_index: int) -> tuple[list[ChunkDraft], int]:
        candidates = [candidate for block in blocks for candidate in self._split_block(block)]
        if not candidates: return [], 0
        if all(self._is_atomic(candidate.block) for candidate in candidates):
            return self._dedupe([self._child(candidate, None, sibling, len(candidates)) for sibling, candidate in enumerate(candidates)], seen)
        parent_text = self._parent_text(candidates)
        make_parent = len(candidates) > 1 or self._tokens.count(parent_text) > self.policy.target_tokens
        output: list[ChunkDraft] = []
        parent_index = global_index if make_parent and parent_text else None
        if parent_index is not None:
            first, last = candidates[0].block, candidates[-1].block
            output.append(ChunkDraft(parent_text, first.content_type, first.page_number, first.section_title,
                {**self._metadata(first, "parent", first.position, last.position, self._tokens.count(parent_text), False, 0), "sibling_count": len(candidates)}))
        output.extend(self._child(candidate, parent_index, sibling, len(candidates)) for sibling, candidate in enumerate(candidates))
        return self._dedupe(output, seen)

    def _split_block(self, block: ChunkingBlock) -> list[ChunkCandidate]:
        text = block.content.strip()
        if self._is_atomic(block):
            return self._split_table(block) if "table" in block.content_type else [ChunkCandidate(block, text, self._tokens.count(text))]
        units = [p.strip() for p in re.split(r"\n\s*\n+", text) if p.strip()]
        segments: list[str] = []; current = ""; semantic_split = False
        for unit in units:
            for sentence in self._sentences(unit):
                candidate = f"{current} {sentence}".strip()
                if (current and self.policy.semantic_enabled and self._tokens.count(current) >= self.policy.min_tokens
                        and self._boundary_detector.is_boundary(current, sentence)):
                    segments.extend(self._hard_split(current)); current = sentence; semantic_split = True
                    continue
                if current and self._tokens.count(candidate) > self.policy.target_tokens:
                    segments.extend(self._hard_split(current)); current = sentence; semantic_split = True
                else: current = candidate
        if current: segments.extend(self._hard_split(current))
        return self._with_overlap([ChunkCandidate(block, s, self._tokens.count(s), semantic_split) for s in segments])

    @staticmethod
    def _sentences(text: str) -> list[str]:
        return [p.strip() for p in re.split(r"(?<=[.!?])\s+(?=[A-Z0-9])", text) if p.strip()]

    def _hard_split(self, text: str) -> list[str]:
        if self._tokens.count(text) <= self.policy.max_tokens: return [text]
        result: list[str] = []
        for sentence in self._sentences(text):
            result.extend([sentence] if self._tokens.count(sentence) <= self.policy.max_tokens else self._tokens.split(sentence, self.policy.max_tokens))
        return result

    def _with_overlap(self, candidates: list[ChunkCandidate]) -> list[ChunkCandidate]:
        if len(candidates) < 2 or not self.policy.overlap_tokens: return candidates
        result = [candidates[0]]
        for previous, current in zip(candidates, candidates[1:]):
            overlap = " ".join(re.findall(r"\S+", previous.content)[-self.policy.overlap_tokens:])
            content = f"{overlap} {current.content}".strip()
            result.append(replace(current, content=content if self._tokens.count(content) <= self.policy.max_tokens else current.content,
                                  token_count=min(self._tokens.count(content), self.policy.max_tokens)))
        return result

    def _split_table(self, block: ChunkingBlock) -> list[ChunkCandidate]:
        lines = [line.strip() for line in block.content.splitlines() if line.strip()]
        if len(lines) < 3 or self._tokens.count(block.content) <= self.policy.max_tokens:
            return [ChunkCandidate(block, block.content.strip(), self._tokens.count(block.content))]
        header, rows, current, result = lines[0], lines[1:], [lines[0]], []
        for row in rows:
            prospective = "\n".join([*current, row])
            if len(current) > 1 and (self._tokens.count(prospective) > self.policy.max_tokens or len(current) - 1 >= self.policy.table_rows_per_group):
                value = "\n".join(current); result.append(ChunkCandidate(block, value, self._tokens.count(value))); current = [header, row]
            else: current.append(row)
        if len(current) > 1:
            value = "\n".join(current); result.append(ChunkCandidate(block, value, self._tokens.count(value)))
        return result

    def _parent_text(self, candidates: list[ChunkCandidate]) -> str:
        parts: list[str] = []; used = 0
        for candidate in candidates:
            if parts and used + candidate.token_count > self.policy.parent_max_tokens: break
            parts.append(candidate.content); used += candidate.token_count
        return "\n\n".join(parts)

    def _child(self, candidate: ChunkCandidate, parent_index: int | None, sibling: int, sibling_count: int) -> ChunkDraft:
        overlap = self.policy.overlap_tokens if sibling and not self._is_atomic(candidate.block) else 0
        metadata = self._metadata(candidate.block, "child", candidate.block.position, candidate.block.position, candidate.token_count, candidate.semantic_split, overlap)
        metadata.update({"sibling_index": sibling, "sibling_count": sibling_count})
        if parent_index is not None: metadata["parent_chunk_index"] = parent_index
        return ChunkDraft(candidate.content, candidate.block.content_type, candidate.block.page_number, candidate.block.section_title, metadata)

    def _metadata(self, block: ChunkingBlock, role: str, start: int, end: int, tokens: int, semantic: bool, overlap: int) -> dict[str, Any]:
        metadata = dict(block.metadata)
        metadata.update(ChunkMetadata(role, start, end, tokens, semantic, overlap, self._is_multimodal(block)).as_dict())
        if block.section_title: metadata.setdefault("heading_path", [block.section_title])
        return metadata

    def _dedupe(self, chunks: list[ChunkDraft], seen: set[str]) -> tuple[list[ChunkDraft], int]:
        kept: list[ChunkDraft] = []; skipped = 0
        for chunk in chunks:
            context = (chunk.content_type, chunk.page_number, chunk.section_title, chunk.metadata.get("sheet_name"), chunk.metadata.get("row_start"), chunk.metadata.get("start_time_ms"))
            signature = hashlib.sha256(repr((" ".join(chunk.content.lower().split()), context)).encode()).hexdigest()
            if signature in seen: skipped += 1; continue
            seen.add(signature); kept.append(chunk)
        if len(kept) == 1 and kept[0].metadata.get("chunk_role") == "parent": kept.clear()
        return kept, skipped

    @staticmethod
    def _structural_key(block: ChunkingBlock) -> tuple[Any, ...]:
        return (block.page_number, block.section_title, block.metadata.get("sheet_name"), block.metadata.get("start_time_ms") if "audio" in block.content_type or "video" in block.content_type else None)
    def _is_atomic(self, block: ChunkingBlock) -> bool: return any(kind in block.content_type for kind in self._ATOMIC_TYPES)
    @staticmethod
    def _is_multimodal(block: ChunkingBlock) -> bool: return bool(block.metadata.get("asset_path") or any(k in block.content_type for k in ("image", "visual", "video")))


class PageAwareChunker:
    """Compatibility adapter; HybridChunkingEngine performs final source planning."""
    def __init__(self, max_chars: int = 1800) -> None: self._max_chars = max_chars
    def text_chunks(self, text: str, *, content_type: str, page_number: int | None = None, section_title: str | None = None, metadata: dict[str, Any] | None = None) -> list[ChunkDraft]:
        parts = [p.strip() for p in text.split("\n\n") if p.strip()]; chunks: list[ChunkDraft] = []; current = ""
        for part in parts:
            candidate = f"{current}\n\n{part}".strip()
            if current and len(candidate) > self._max_chars:
                chunks.append(ChunkDraft(current, content_type, page_number, section_title, metadata or {})); current = part
            else: current = candidate
        if current: chunks.append(ChunkDraft(current, content_type, page_number, section_title, metadata or {}))
        return chunks
