import asyncio

from fastapi import FastAPI, HTTPException

from app.config import settings
from app.services.code_store import CodeStateStore
from app.services.scraper import ShiftCodeScraper
from app.services.submitter import ShiftCodeSubmitter

app = FastAPI(title=settings.app_name)

code_store = CodeStateStore(
    unsubmitted_path=settings.unsubmitted_codes_path,
    submitted_path=settings.submitted_codes_path,
)
scraper = ShiftCodeScraper(
    store=code_store,
    timeout_seconds=settings.request_timeout_seconds,
)
submitter = ShiftCodeSubmitter(settings=settings)


@app.get("/health")
async def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/codes")
async def get_code_state() -> dict[str, object]:
    return await asyncio.to_thread(code_store.load_state)


@app.post("/scrape")
async def scrape_codes() -> dict[str, object]:
    result = await scraper.scrape(settings.scrape_sources)
    return result.model_dump(mode="json")


@app.post("/submit-codes")
async def submit_codes() -> dict[str, object]:
    unsubmitted = await asyncio.to_thread(code_store.load_unsubmitted)
    if not unsubmitted.codes:
        return {
            "attempted_codes": 0,
            "processed_codes": [],
            "remaining_unsubmitted_codes": 0,
            "detail": "No unsubmitted codes were available.",
        }

    try:
        submission_result = await submitter.submit_codes(unsubmitted.codes)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Failed to submit codes through SHiFT: {exc}",
        ) from exc

    persisted_result = await asyncio.to_thread(
        code_store.persist_submission_results,
        submission_result,
    )
    return persisted_result.model_dump(mode="json")
