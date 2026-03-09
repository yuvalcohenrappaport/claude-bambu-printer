from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="BAMBU_", env_file=".env")

    host: str = "0.0.0.0"
    port: int = 8000
    project_root: Path = Path(__file__).parent.parent.parent  # repo root
    log_file: str = "backend/logs/app.log"
    heartbeat_interval: int = 20  # seconds
    heartbeat_timeout: int = 10  # seconds
    grace_period: int = 30  # seconds
    idle_warning: int = 720  # 12 minutes in seconds
    idle_timeout: int = 900  # 15 minutes in seconds
    claude_connect_timeout: int = 30  # seconds


settings = Settings()
