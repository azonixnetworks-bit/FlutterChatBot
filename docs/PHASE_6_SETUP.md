# Phase 6 — PDF Multimodal Ingestion

Phase 6 adds a backend-only PDF worker. It extracts native text page by page, uses OCR only for low-text pages, represents tables as readable rows, and retains useful visual assets in the private `knowledge-files` bucket. Chunks keep page, heading, extraction method, nearby context, and private asset-path metadata. No private URL or server key is returned to Flutter.

## Apply migration

Run `supabase/migrations/202610080003_phase5_phase6_ingestion.sql` after the earlier migrations. It adds the `analyzing` source state and an atomic replace-and-complete RPC. Reprocessing replaces a source's chunks in one transaction.

## Backend requirements

Install `backend/requirements.txt`. `PyMuPDF` is required. OCR uses `pytesseract`; install the Tesseract executable on a worker host to enable OCR for scanned PDFs. Without it, scanned pages do not fail the entire PDF, but yield no OCR text.

## Run a queued job

After upload and queueing, call the authenticated endpoint:

`POST /knowledge/jobs/{job_id}/run`

The caller can run only their own job. The backend verifies ownership before it downloads from private storage. Processing progresses through `extracting`, `analyzing`, `chunking`, then `ready`; failures mark both job and source as `failed`.

The endpoint is intentionally synchronous for the current development worker. Production scheduling/worker orchestration remains a later deployment concern.
