from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies.auth import get_current_user
from app.api.dependencies.supabase import get_supabase_data_service
from app.schemas.auth import AuthUser
from app.schemas.knowledge import QueueProcessingJobRequest, ProcessingJobResponse
from app.services.supabase_data import SupabaseDataError, SupabaseDataService

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


@router.post(
    "/jobs",
    response_model=ProcessingJobResponse,
    status_code=status.HTTP_201_CREATED,
)
async def queue_processing_job(
    body: QueueProcessingJobRequest,
    user: AuthUser = Depends(get_current_user),
    service: SupabaseDataService = Depends(get_supabase_data_service),
) -> ProcessingJobResponse:
    try:
        return await service.enqueue_processing_job(
            user_id=user.id,
            source_id=str(body.source_id),
            job_type=body.job_type,
        )
    except SupabaseDataError as exc:
        if "not found" in exc.message.lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Knowledge source not found.",
            ) from exc

        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Unable to queue the processing job.",
        ) from exc


@router.get("/jobs/{job_id}", response_model=ProcessingJobResponse)
async def get_processing_job(
    job_id: UUID,
    user: AuthUser = Depends(get_current_user),
    service: SupabaseDataService = Depends(get_supabase_data_service),
) -> ProcessingJobResponse:
    try:
        job = await service.get_processing_job(
            user_id=user.id,
            job_id=str(job_id),
        )
    except SupabaseDataError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Unable to load the processing job.",
        ) from exc

    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Processing job not found.",
        )

    return job
