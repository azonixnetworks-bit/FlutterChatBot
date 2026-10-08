import httpx

from app.core.config import Settings
from app.schemas.auth import AuthUser


class InvalidSupabaseTokenError(Exception):
    pass


class SupabaseAuthService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def get_user(self, access_token: str) -> AuthUser:
        url = f"{self._settings.supabase_url.rstrip('/')}/auth/v1/user"
        headers = {
            "apikey": self._settings.supabase_anon_key,
            "Authorization": f"Bearer {access_token}",
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, headers=headers)

        if response.status_code in {401, 403}:
            raise InvalidSupabaseTokenError

        response.raise_for_status()
        payload = response.json()

        return AuthUser(
            id=str(payload["id"]),
            email=payload.get("email"),
        )
