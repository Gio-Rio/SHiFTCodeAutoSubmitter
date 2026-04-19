from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "SHiFT Code Auto Submitter"
    data_dir: Path = Path("data")
    unsubmitted_codes_path: Path = Path("data/unsubmitted_codes.json")
    submitted_codes_path: Path = Path("data/submitted_codes.json")
    request_timeout_seconds: float = 15.0
    username: str | None = None
    password: str | None = None
    shift_home_url: str = "https://shift.gearboxsoftware.com/home"
    login_max_attempts: int = 3
    headless_browser: bool = False
    target_game: str = "Borderlands 4"
    target_platform_button_text: str = "Redeem for PSN"
    check_button_text: str = "CHECK"
    invalid_code_message: str = "This SHiFT code does not exist"
    platform_selection_message: str = (
        "Please select the platform and game you'd like to receive your SHiFT rewards."
    )
    already_redeemed_markers: list[str] = Field(
        default_factory=lambda: [
            "already redeemed",
            "already been redeemed",
            "has already been redeemed",
        ]
    )
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
