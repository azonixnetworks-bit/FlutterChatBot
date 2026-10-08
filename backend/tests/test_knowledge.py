from datetime import UTC, datetime

from fastapi.testclient import TestClient

from app.api.dependencies.auth import get_current_user
from app.api.dependencies.supabase import get_supabase_data_service
from app.main import app
from app.schemas.auth import AuthUser
from app.schemas.knowledge import ProcessingJobResponse

USER_ID = "11111111-1111-1111-1111-111111111111"
SOURCE_ID = "22222222-2222-2222-2222-222222222222"
JOB_ID = "33333333-3333-3333-3333-333333333333"


class FakeDataService:
    async def enqueue_processing_job(
        self,
        *,
        user_id: str,
        source_id: str,
        job_type: str,
    ) -> ProcessingJobResponse:
        assert user_id == USER_ID
        assert source_id == SOURCE_ID
        assert job_type == "ingest"
        return _job()

    async def get_processing_job(
        self,
        *,
        user_id: str,
        job_id: str,
    ) -> ProcessingJobResponse | None:
        assert user_id == USER_ID
        if job_id != JOB_ID:
            return None
        return _job()


def _job() -> ProcessingJobResponse:
    return ProcessingJobResponse(
        id=JOB_ID,
        user_id=USER_ID,
        source_id=SOURCE_ID,
        job_type="ingest",
        status="queued",
        progress=0,
        current_step="Waiting for processing worker",
        error_message=None,
        created_at=datetime(2026, 10, 8, tzinfo=UTC),
    )


def _override_user() -> AuthUser:
    return AuthUser(id=USER_ID, email="user@example.com")


def _override_service() -> FakeDataService:
    return FakeDataService()


def setup_module() -> None:
    app.dependency_overrides[get_current_user] = _override_user
    app.dependency_overrides[get_supabase_data_service] = _override_service


def teardown_module() -> None:
    app.dependency_overrides.clear()


client = TestClient(app)


def test_queue_processing_job() -> None:
    response = client.post(
        "/knowledge/jobs",
        json={"source_id": SOURCE_ID, "job_type": "ingest"},
    )

    assert response.status_code == 201
    assert response.json()["id"] == JOB_ID
    assert response.json()["status"] == "queued"


def test_get_processing_job() -> None:
    response = client.get(f"/knowledge/jobs/{JOB_ID}")

    assert response.status_code == 200
    assert response.json()["source_id"] == SOURCE_ID


def test_get_processing_job_not_found() -> None:
    response = client.get("/knowledge/jobs/44444444-4444-4444-4444-444444444444")

    assert response.status_code == 404
