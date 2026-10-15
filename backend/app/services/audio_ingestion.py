from dataclasses import dataclass
from typing import Protocol
from app.services.chunking import ChunkDraft

@dataclass(frozen=True)
class TranscriptSegment:
    start_ms: int
    end_ms: int
    text: str
    language: str | None = None
    speaker: str | None = None
    confidence: float | None = None

class SpeechToTextProvider(Protocol):
    def transcribe(self, audio: bytes, *, file_type: str) -> list[TranscriptSegment]: ...

class AudioIngestionError(ValueError): pass

class AudioExtractor:
    def __init__(self, provider: SpeechToTextProvider | None = None, max_bytes: int = 200_000_000) -> None:
        self._provider=provider; self._max_bytes=max_bytes
    def extract(self, data: bytes, *, file_type: str, source_id: str) -> list[ChunkDraft]:
        if not data: raise AudioIngestionError("The audio file is empty.")
        if len(data)>self._max_bytes: raise AudioIngestionError("Audio exceeds configured size limit.")
        if file_type not in {"mp3","wav","m4a","aac"}: raise AudioIngestionError("Unsupported audio type.")
        if not self._provider: return []
        chunks=[]; previous=""
        for segment in self._provider.transcribe(data,file_type=file_type):
            text=" ".join(segment.text.split())
            if not text or text==previous: continue
            previous=text
            chunks.append(ChunkDraft(text,"audio_transcript",metadata={"source_id":source_id,"start_time_ms":segment.start_ms,"end_time_ms":segment.end_ms,"language":segment.language,"speaker":segment.speaker,"confidence":segment.confidence,"extraction_method":"stt_provider"}))
        return chunks
