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
    expired_code_message: str = "This SHiFT code has expired"
    between_submissions_pause_seconds: float = 0.75
    # Max time to wait for CHECK to become enabled again (often disabled while the last request finishes).
    check_button_ready_timeout_seconds: float = 90.0
    platform_selection_message: str = (
        "Please select the platform and game you'd like to receive your SHiFT rewards."
    )
    # Substrings matched against page text (after CHECK); more resilient than one long exact line.
    platform_selection_markers: list[str] = Field(
        default_factory=lambda: [
            "please select the platform",
            "receive your shift rewards",
        ]
    )
    code_validation_poll_interval_seconds: float = 0.25
    code_validation_max_polls: int = 240
    redemption_max_polls: int = 120
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
            "https://mobalytics.gg/borderlands-4/shift-codes-borderlands-4",
            "https://game8.co/games/Borderlands-4/archives/548406",
            "https://xsmashx88x.github.io/bl4shiftcodes/",
            "https://gamesradar.com/games/borderlands/borderlands-4-shift-codes-golden-keys/",
            "https://shift.gearboxsoftware.com/home",
        ]
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


settings = Settings()
