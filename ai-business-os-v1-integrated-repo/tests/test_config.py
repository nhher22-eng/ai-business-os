from app.core.config import settings


def test_application_config_contract():
    assert settings.app_name
    assert settings.app_port == 8000
    assert settings.database_url.startswith("postgresql+psycopg://")
    assert settings.redis_url.startswith("redis://")


def test_runtime_intervals_are_positive():
    assert settings.worker_poll_seconds > 0
    assert settings.scheduler_interval_seconds > 0
