from app.services.video_ingestion import select_keyframes, nearby_transcript, analyze_keyframe

def test_keyframes_are_bounded_and_deduplicated():
 frames=select_keyframes([(0,b'a'),(1000,b'a'),(6000,b'b')],min_gap_ms=5000)
 assert len(frames)==2 and frames[0].reason=='first_frame'
def test_nearby_speech_context():
 assert nearby_transcript(10000,[{'start_time_ms':9000,'end_time_ms':11000},{'start_time_ms':40000,'end_time_ms':41000}])==[{'start_time_ms':9000,'end_time_ms':11000}]
def test_provider_unavailable_has_no_fake_frame_knowledge():
 assert analyze_keyframe(select_keyframes([(0,b'a')])[0])==[]
