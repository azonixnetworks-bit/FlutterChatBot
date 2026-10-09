# Phase 5 — TXT/Text Ingestion

The backend worker now processes queued TXT sources with the shared, intentionally simple `PageAwareChunker`. It uses a backend-only private-storage download, records progress, atomically replaces previous chunks for the source, and marks the job/source ready or failed together.

Run a job through the authenticated `POST /knowledge/jobs/{job_id}/run` endpoint after applying the Phase 5/6 migration. This shared worker foundation is extended by Phase 6 for PDF ingestion; it is not the Phase 12 hybrid chunking engine.
