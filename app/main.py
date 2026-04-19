from fastapi import FastAPI

from app.config import settings
from app.services.code_store import CodeStore
from app.services.scraper import ShiftCodeScraper

app = FastAPI(title=settings.app_name)

code_store = CodeStore(settings.code_store_path)
scraper = ShiftCodeScraper(
    store=code_store,
    timeout_seconds=settings.request_timeout_seconds,
)


@app.get("/health")
async def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/codes")
async def get_known_codes() -> dict[str, object]:
    stored = code_store.load()
    return stored.model_dump(mode="json")


@app.post("/scrape")
async def scrape_codes() -> dict[str, object]:
    result = await scraper.scrape(settings.scrape_sources)
    return result.model_dump(mode="json")
