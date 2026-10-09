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

    async def get_owned_source(self, *, user_id: str, source_id: str) -> dict[str, Any] | None:
        return await self._get_one("knowledge_sources", {"id": f"eq.{source_id}", "user_id": f"eq.{user_id}"})

    async def download_private_file(self, *, bucket: str, path: str) -> bytes:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.get(f"{self._base_url}/storage/v1/object/{bucket}/{path}", headers=self._headers())
        if response.is_error:
            raise self._to_error(response)
        return response.content

    async def upload_private_file(self, *, bucket: str, path: str, data: bytes, content_type: str) -> None:
        headers = self._headers()
        headers["Content-Type"] = content_type
        headers["x-upsert"] = "false"
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(f"{self._base_url}/storage/v1/object/{bucket}/{path}", headers=headers, content=data)
        if response.is_error:
            raise self._to_error(response)

    async def update_progress(self, *, user_id: str, source_id: str, job_id: str, source_status: str, progress: int, step: str) -> None:
        await self._patch("knowledge_sources", {"id": f"eq.{source_id}", "user_id": f"eq.{user_id}"}, {"status": source_status, "error_message": None})
        await self._patch("processing_jobs", {"id": f"eq.{job_id}", "user_id": f"eq.{user_id}"}, {"status": "processing", "progress": progress, "current_step": step})

    async def replace_chunks_and_complete(self, *, user_id: str, source_id: str, job_id: str, chunks: list[dict[str, Any]]) -> None:
        payload = {"p_user_id": user_id, "p_source_id": source_id, "p_job_id": job_id, "p_chunks": chunks}
        await self._rpc("replace_knowledge_chunks_and_complete", payload)

    async def fail_processing(self, *, user_id: str, source_id: str, job_id: str, message: str) -> None:
        safe_message = message[:1000]
        await self._patch("knowledge_sources", {"id": f"eq.{source_id}", "user_id": f"eq.{user_id}"}, {"status": "failed", "error_message": safe_message})
        await self._patch("processing_jobs", {"id": f"eq.{job_id}", "user_id": f"eq.{user_id}"}, {"status": "failed", "error_message": safe_message, "completed_at": "now()"})

    async def _get_one(self, table: str, params: dict[str, str]) -> dict[str, Any] | None:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(f"{self._base_url}/rest/v1/{table}", headers=self._headers(), params={**params, "limit": "1"})
        if response.is_error:
            raise self._to_error(response)
        rows = response.json()
        return rows[0] if rows else None

    async def _patch(self, table: str, params: dict[str, str], payload: dict[str, Any]) -> None:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.patch(f"{self._base_url}/rest/v1/{table}", headers=self._headers(), params=params, json=payload)
        if response.is_error:
            raise self._to_error(response)

    async def _rpc(self, name: str, payload: dict[str, Any]) -> None:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(f"{self._base_url}/rest/v1/rpc/{name}", headers=self._headers(), json=payload)
        if response.is_error:
            raise self._to_error(response)

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
