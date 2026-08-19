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

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )


settings = Settings()
