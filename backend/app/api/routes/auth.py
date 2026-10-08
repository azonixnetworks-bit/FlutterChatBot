from fastapi import APIRouter, Depends

from app.api.dependencies.auth import get_current_user
from app.schemas.auth import AuthUser

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/me", response_model=AuthUser)
async def auth_me(user: AuthUser = Depends(get_current_user)) -> AuthUser:
    return user
