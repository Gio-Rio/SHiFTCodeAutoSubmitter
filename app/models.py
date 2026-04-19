from datetime import datetime, timezone
from enum import StrEnum

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class UnsubmittedCodes(BaseModel):
    codes: list[str] = Field(default_factory=list)
    last_updated_at: datetime | None = None


class SubmittedCodes(BaseModel):
    successful_codes: list[str] = Field(default_factory=list)
    unsuccessful_codes: list[str] = Field(default_factory=list)
    already_redeemed_codes: list[str] = Field(default_factory=list)
    last_updated_at: datetime | None = None


class ScrapeResult(BaseModel):
    scanned_sources: list[str]
    found_codes: list[str]
    new_codes: list[str]
    queued_code_count: int
    last_scraped_at: datetime = Field(default_factory=utc_now)


class SubmissionStatus(StrEnum):
    SUCCESSFUL = "successful"
    UNSUCCESSFUL = "unsuccessful"
    ALREADY_REDEEMED = "already_redeemed"
    EXPIRED = "expired"


class CodeSubmissionOutcome(BaseModel):
    code: str
    status: SubmissionStatus
    detail: str | None = None


class SubmissionResult(BaseModel):
    attempted_codes: int
    processed_codes: list[CodeSubmissionOutcome]
    remaining_unsubmitted_codes: int
    login_attempts: int
    target_game: str
    target_platform: str
    finished_at: datetime = Field(default_factory=utc_now)
