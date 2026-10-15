# Phase 9 — Standalone Image OCR + Vision

Private standalone images are validated server-side with dimension/pixel limits. Swappable OCR and Vision providers add grounded chunks only when configured; otherwise no placeholder knowledge is created and the source can be reprocessed later. Chunks retain only the original private storage path, never bytes or signed URLs.
