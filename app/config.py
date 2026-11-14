"""Application configuration using Pydantic Settings."""

from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Trailmark application settings with sensible defaults."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    APP_NAME: str = "Trailmark"
    DATA_DIR: str = "data"
    LLM_PROVIDER: str = "mock"
    LLM_API_KEY: str = ""
    LLM_MODEL: str = "mock-model"
    MAX_INPUT_CHARS: int = 40000
    MAX_FILE_BYTES: int = 1000000  # ~1MB
    RUNS_PER_HOUR: int = 6

    @property
    def data_path(self) -> Path:
        """Return the resolved Path for the data directory and ensure it exists."""
        path = Path(self.DATA_DIR)
        path.mkdir(parents=True, exist_ok=True)
        return path


settings = Settings()
