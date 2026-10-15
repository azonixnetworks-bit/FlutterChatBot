# Phase 12 — Hybrid Chunking Engine

Phase 12 replaces the temporary final chunk handoff with one backend-only, deterministic chunk planner. Extractors still produce ordered `ChunkDraft` records; `KnowledgeProcessingService` normalizes them into blocks, plans a complete tree, then invokes the existing atomic replacement RPC.

## Strategy

- Structural boundaries win: page, section, sheet, table/visual record, and timestamp metadata are retained.
- Prose prefers paragraph and sentence boundaries. A deterministic lexical boundary fallback is used when no semantic provider is configured. No embeddings are generated or stored.
- Parent chunks hold wider section context. Retrieval-sized children carry `parent_chunk_index` during the request; the database function resolves it to `parent_chunk_id` atomically.
- Tables are grouped by rows with their header repeated. Tables and isolated visuals receive no overlap.
- Content and location/context participate in duplicate detection, so duplicate text on separate pages or times remains valid knowledge.

## Configuration

Set these optional backend environment variables in `backend/.env`:

```env
CHUNK_TARGET_TOKENS=650
CHUNK_MAX_TOKENS=800
CHUNK_MIN_TOKENS=80
CHUNK_OVERLAP_TOKENS=80
PARENT_CHUNK_TARGET_TOKENS=1400
PARENT_CHUNK_MAX_TOKENS=1800
SEMANTIC_CHUNKING_ENABLED=true
MULTIMODAL_CONTEXT_WINDOW_MS=30000
TABLE_ROWS_PER_GROUP=25
```

The fallback counter is a deterministic whitespace-token estimate and records `token_count_estimated: true`. Invalid limits fail processing configuration validation rather than silently producing oversized chunks.

## Migration

Apply `supabase/migrations/202610150002_phase12_hybrid_chunking.sql` after the earlier migrations. It changes only the trusted `replace_knowledge_chunks_and_complete` function; it does not add public access, alter RLS, or expose private Storage URLs.

Existing sources remain readable. Reprocessing replaces all chunks for a source in one transaction, including the complete parent/child tree.
