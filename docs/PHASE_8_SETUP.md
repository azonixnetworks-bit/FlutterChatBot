# Phase 8 — CSV + Excel Multimodal Ingestion

CSV and XLS/XLSX sources are read through the authenticated worker. Header-aware rows are stored as searchable `spreadsheet_table` chunks with sheet and row metadata. Existing owner checks and atomic replacement protect reprocessing. No migration is required.
