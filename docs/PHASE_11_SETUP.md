# Phase 11 — Video Multimodal Processing

FFmpeg and ffprobe are required. Video probing is bounded by size, duration and subprocess timeout; temporary input files are removed automatically. Keyframe selection is bounded and duplicate-suppressed. OCR, Vision, and STT hooks emit only configured-provider output; otherwise videos remain reprocessable without fabricated knowledge.
