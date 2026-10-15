# Phase 10 — Audio Transcription + Timestamp Knowledge

Apply `supabase/migrations/202610150001_phase10_audio_timestamps.sql`. Audio sources are validated server-side and passed only to a configured `SpeechToTextProvider`. Transcript segments retain millisecond start/end times, language, speaker, and confidence. With no provider configured, no transcript is fabricated and the source remains reprocessable.
