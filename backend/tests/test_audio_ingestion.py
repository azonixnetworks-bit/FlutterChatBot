from app.services.audio_ingestion import AudioExtractor, TranscriptSegment, AudioIngestionError
import pytest
class Provider:
 def transcribe(self,audio,*,file_type): return [TranscriptSegment(1000,2500,"வணக்கம் world",language="ta",speaker="Speaker 1"),TranscriptSegment(1000,2500,"வணக்கம் world")]
def test_timestamped_transcript_and_dedup():
 chunks=AudioExtractor(Provider()).extract(b"audio",file_type="mp3",source_id="s")
 assert len(chunks)==1 and chunks[0].metadata["start_time_ms"]==1000
def test_provider_unavailable_creates_no_fake_transcript():
 assert AudioExtractor().extract(b"audio",file_type="wav",source_id="s")==[]
def test_limits_and_type():
 with pytest.raises(AudioIngestionError): AudioExtractor(max_bytes=1).extract(b"xx",file_type="mp3",source_id="s")
