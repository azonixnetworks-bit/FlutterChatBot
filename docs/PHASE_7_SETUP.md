# Phase 7 — DOCX Multimodal Ingestion

DOCX processing uses the existing authenticated worker and atomic source replacement. It preserves heading levels, paragraphs, lists, table rows/headers, document position, and nearby text. Useful images remain private; chunks hold only metadata references. Without a configured vision provider, visual chunks are marked `pending_provider` rather than fabricating a description.
