from typing import Any

import httpx

from app.core.config import Settings
from app.schemas.knowledge import ProcessingJobResponse


class SupabaseDataError(Exception):
    def __init__(self, status_code: int, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.message = message


class SupabaseDataService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._base_url = settings.supabase_url.rstrip("/")
        self._server_key = settings.supabase_server_key

    def _headers(self, *, prefer: str | None = None) -> dict[str, str]:
        headers = {
            "apikey": self._server_key,
            "Content-Type": "application/json",
        }

        if not self._server_key.startswith("sb_secret_"):
            headers["Authorization"] = f"Bearer {self._server_key}"

        if prefer:
            headers["Prefer"] = prefer

        return headers

    async def enqueue_processing_job(
        self,
        *,
        user_id: str,
        source_id: str,
        job_type: str,
    ) -> ProcessingJobResponse:
        payload = {
            "p_user_id": user_id,
            "p_source_id": source_id,
            "p_job_type": job_type,
        }

        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                f"{self._base_url}/rest/v1/rpc/enqueue_processing_job",
                headers=self._headers(),
                json=payload,
            )

        if response.is_error:
            raise self._to_error(response)

        data: Any = response.json()
        if isinstance(data, list):
            if not data:
                raise SupabaseDataError(502, "Supabase returned an empty job result.")
            data = data[0]

        return ProcessingJobResponse.model_validate(data)

    async def get_processing_job(
        self,
        *,
        user_id: str,
        job_id: str,
    ) -> ProcessingJobResponse | None:
        params = {
            "id": f"eq.{job_id}",
            "user_id": f"eq.{user_id}",
            "limit": "1",
        }

        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(
                f"{self._base_url}/rest/v1/processing_jobs",
                headers=self._headers(),
                params=params,
            )

        if response.is_error:
            raise self._to_error(response)

        rows = response.json()
        if not rows:
            return None

        return ProcessingJobResponse.model_validate(rows[0])

    @staticmethod
    def _to_error(response: httpx.Response) -> SupabaseDataError:
        message = "Supabase data request failed."
        try:
            payload = response.json()
            message = (
                payload.get("message")
                or payload.get("details")
                or payload.get("hint")
                or message
            )
        except ValueError:
            if response.text:
                message = response.text

        return SupabaseDataError(response.status_code, str(message))
