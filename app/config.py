from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="DOCPARSE_", extra="ignore")

    host: str = "0.0.0.0"
    port: int = 8787
    max_upload_mb: int = 50
    # stub | none | rapid
    ocr_provider: str = "rapid"
    ocr_scale: float = 2.0
    ocr_max_pages: int = 50
    api_keys: str = ""  # comma-separated; empty = auth disabled
    jobs_dir: str = "data/jobs"
    job_workers: int = 1

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024

    @property
    def api_key_set(self) -> set[str]:
        return {k.strip() for k in self.api_keys.split(",") if k.strip()}

    @property
    def jobs_dir_path(self) -> Path:
        return Path(self.jobs_dir)


@lru_cache
def get_settings() -> Settings:
    return Settings()
