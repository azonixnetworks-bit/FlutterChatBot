from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class QueueProcessingJobRequest(BaseModel):
    source_id: UUID
    job_type: str = Field(default="ingest", min_length=1, max_length=64)


class ProcessingJobResponse(BaseModel):
    id: UUID
    user_id: UUID
    source_id: UUID
    job_type: str
    status: str
    progress: int
    current_step: str | None = None
    error_message: str | None = None
    created_at: datetime
