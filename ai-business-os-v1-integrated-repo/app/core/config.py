from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "production"
    app_name: str = "AI Business OS"
    app_port: int = 8000

    database_url: str = (
        "postgresql+psycopg://aios:change-me@postgres:5432/aios"
    )
    redis_url: str = "redis://redis:6379/0"

    secret_key: str = "CHANGE_ME"

    # M-20.4:
    # Dedicated operator credential for privileged Agent Control API.
    # Empty means fail closed.
    agent_control_api_token: str = ""

    worker_poll_seconds: float = 1.0
    scheduler_interval_seconds: float = 10.0

    # M-05 / M-06 content studio
    media_root: str = "/app/data"
    asset_storage_provider: str = "local"
    asset_storage_root: str = "/app/data/asset-workflows"
    openai_api_key: str = ""
    openai_api_base: str = "https://api.openai.com/v1"
    openai_image_model: str = "gpt-image-2"
    image_preview_quality: str = "low"
    image_final_quality: str = "high"
    image_request_timeout_seconds: float = 180.0
    image_max_preview_generations: int = 8
    image_max_final_generations: int = 3
    image_preview_estimated_cost_micros: int = 0
    image_final_estimated_cost_micros: int = 0

    google_drive_client_id: str = ""
    google_drive_client_secret: str = ""
    google_drive_redirect_uri: str = "https://os.gardenfarm.kr/api/v1/integrations/google-drive/callback"
    google_drive_root_folder_id: str = ""
    google_picker_api_key: str = ""
    google_picker_app_id: str = ""

    canva_client_id: str = ""
    canva_client_secret: str = ""
    canva_redirect_uri: str = "https://os.gardenfarm.kr/api/v1/integrations/canva/callback"

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )


settings = Settings()
