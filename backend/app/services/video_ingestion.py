"""Phase 11 bounded FFmpeg video probe/keyframe foundation."""
from dataclasses import dataclass
import json, subprocess, tempfile
from pathlib import Path
import hashlib
from typing import Protocol

class VideoIngestionError(ValueError): pass
@dataclass(frozen=True)
class VideoMetadata:
    duration_ms:int; width:int; height:int; frame_rate:str; format:str; has_audio:bool
class VideoProbe:
 def __init__(self,max_bytes=500_000_000,max_duration_ms=7_200_000): self.max_bytes=max_bytes; self.max_duration_ms=max_duration_ms
 def probe(self,data:bytes,file_type:str)->VideoMetadata:
  if not data or file_type not in {'mp4','mov','mkv','webm'}: raise VideoIngestionError('Invalid or unsupported video.')
  if len(data)>self.max_bytes: raise VideoIngestionError('Video exceeds configured size limit.')
  with tempfile.TemporaryDirectory() as directory:
   path=Path(directory)/f'video.{file_type}'; path.write_bytes(data)
   try: result=subprocess.run(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(path)],capture_output=True,text=True,check=True,timeout=30)
   except Exception as exc: raise VideoIngestionError('Video is corrupted or unreadable.') from exc
  payload=json.loads(result.stdout); streams=payload.get('streams',[]); video=next((s for s in streams if s.get('codec_type')=='video'),None)
  if not video: raise VideoIngestionError('Video stream not found.')
  duration_ms=int(float(payload.get('format',{}).get('duration',0))*1000)
  if not duration_ms or duration_ms>self.max_duration_ms: raise VideoIngestionError('Video duration is invalid or exceeds the limit.')
  return VideoMetadata(duration_ms,int(video.get('width',0)),int(video.get('height',0)),video.get('r_frame_rate',''),payload.get('format',{}).get('format_name',''),any(s.get('codec_type')=='audio' for s in streams))

@dataclass(frozen=True)
class Keyframe:
 timestamp_ms:int; data:bytes; scene_index:int; reason:str
def select_keyframes(frames:list[tuple[int,bytes]], *, min_gap_ms:int=5_000,max_frames:int=24)->list[Keyframe]:
 """Deterministic bounded sampling; identical frames and close frames are suppressed."""
 selected=[]; seen=set(); last=-min_gap_ms
 for timestamp,data in frames:
  digest=hashlib.sha256(data).digest()
  if digest in seen or timestamp-last<min_gap_ms: continue
  seen.add(digest); selected.append(Keyframe(timestamp,data,len(selected),"first_frame" if not selected else "periodic_sample")); last=timestamp
  if len(selected)>=max_frames: break
 return selected

class FrameOcrProvider(Protocol):
 def extract(self, frame:bytes)->tuple[str,dict]: ...
class FrameVisionProvider(Protocol):
 def describe(self, frame:bytes)->tuple[str,str,dict]: ...
def analyze_keyframe(frame:Keyframe, *, ocr:FrameOcrProvider|None=None, vision:FrameVisionProvider|None=None)->list[dict]:
 """Provider hooks return only grounded provider output; unavailable providers add no knowledge."""
 result=[]; base={"timestamp_ms":frame.timestamp_ms,"scene_index":frame.scene_index,"extraction_reason":frame.reason}
 if ocr:
  text,details=ocr.extract(frame.data)
  if text.strip(): result.append({"content":text.strip(),"content_type":"video_frame_ocr","metadata":{**base,"ocr":details}})
 if vision:
  text,kind,details=vision.describe(frame.data)
  if text.strip(): result.append({"content":text.strip(),"content_type":kind,"metadata":{**base,"vision":details}})
 return result

def nearby_transcript(timestamp_ms:int, segments:list[dict], window_ms:int=15_000)->list[dict]:
 """Associate only speech close to a selected frame; provider output stays untouched."""
 return [s for s in segments if s.get('start_time_ms',0)<=timestamp_ms+window_ms and s.get('end_time_ms',0)>=timestamp_ms-window_ms]
