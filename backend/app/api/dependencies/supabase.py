from fastapi import Depends, HTTPException, status

from app.core.config import Settings, get_settings
from app.services.supabase_data import SupabaseDataService


def get_supabase_data_service(
    settings: Settings = Depends(get_settings),
) -> SupabaseDataService:
    if not settings.supabase_admin_configured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Supabase backend secret key is not configured.",
        )

    return SupabaseDataService(settings)
