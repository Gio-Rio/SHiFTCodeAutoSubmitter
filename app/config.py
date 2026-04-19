from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "SHiFT Code Auto Submitter"
    data_dir: Path = Path("data")
    code_store_path: Path = Path("data/discovered_codes.json")
    request_timeout_seconds: float = 15.0
    # Reserved for future Gearbox / SHiFT redemption; optional so startup works without them.
    username: str | None = None
    password: str | None = None
    scrape_sources: list[str] = Field(
        default_factory=lambda: [
            "https://mentalmars.com/game-news/borderlands-4-shift-codes/",
            "https://shift.orcicorn.com/",
        ]
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


settings = Settings()
