from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Multimodal Knowledge API"
    app_env: str = "development"
    app_debug: bool = True
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    cors_origins: str = "http://localhost:3000,http://localhost:5173"
    cors_origin_regex: str = r"^http://(localhost|127\.0\.0\.1):\d+$"

    supabase_url: str = ""
    supabase_publishable_key: str = ""
    supabase_anon_key: str = ""
    supabase_secret_key: str = ""
    supabase_service_role_key: str = ""

    ai_provider: str = ""
    llm_model: str = ""
    embedding_provider: str = ""
    embedding_model: str = ""
    embedding_dimension: str = ""
    vision_provider: str = ""
    vision_model: str = ""
    stt_provider: str = ""
    stt_model: str = ""
    reranker_provider: str = ""
    reranker_model: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def cors_origin_list(self) -> list[str]:
        return [x.strip() for x in self.cors_origins.split(",") if x.strip()]

    @property
    def supabase_client_key(self) -> str:
        return self.supabase_publishable_key.strip() or self.supabase_anon_key.strip()

    @property
    def supabase_server_key(self) -> str:
        return self.supabase_secret_key.strip() or self.supabase_service_role_key.strip()

    @property
    def supabase_auth_configured(self) -> bool:
        return bool(self.supabase_url.strip() and self.supabase_client_key)

    @property
    def supabase_admin_configured(self) -> bool:
        return bool(self.supabase_url.strip() and self.supabase_server_key)


@lru_cache
def get_settings() -> Settings:
    return Settings()
