from datetime import datetime, timezone

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class StoredCodes(BaseModel):
    known_codes: list[str] = Field(default_factory=list)
    last_scraped_at: datetime | None = None


class ScrapeResult(BaseModel):
    scanned_sources: list[str]
    found_codes: list[str]
    new_codes: list[str]
    known_code_count: int
    last_scraped_at: datetime = Field(default_factory=utc_now)
