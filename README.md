# SHiFTCodeAutoSubmitter

Automatically search the web to find new SHiFT codes, queue unsubmitted ones, and submit them to Gearbox through an API-backed Playwright flow.

## Stack

- FastAPI
- httpx
- BeautifulSoup
- Playwright
- JSON file persistence

## Endpoints

- `GET /health` returns a simple health status
- `GET /codes` returns both unsubmitted and submitted code state
- `POST /scrape` fetches configured source pages, extracts SHiFT-style codes, and appends only brand-new ones to `data/unsubmitted_codes.json`
- `POST /submit-codes` logs into SHiFT, checks each queued code, redeems valid ones for the configured game/platform, and moves processed codes into `data/submitted_codes.json`

## Local setup

1. Create a virtual environment and activate it.
2. Install dependencies:

```bash
pip install -e ".[dev]"
playwright install chromium
```

3. Copy `.env.example` to `.env` if you want to override defaults.
4. Run the API:

```bash
uvicorn app.main:app --reload
```

## Notes

- New scraper discoveries land in `data/unsubmitted_codes.json`.
- Submission results are stored in `data/submitted_codes.json` under `successful_codes`, `unsuccessful_codes`, and `already_redeemed_codes`.
- The Playwright flow uses `.env` values for `USERNAME`, `PASSWORD`, `TARGET_GAME`, and `TARGET_PLATFORM_BUTTON_TEXT`.
- Login retries default to `3`, and the browser defaults to visible mode with `HEADLESS_BROWSER=false`.
- The scraper uses a SHiFT code pattern of `XXXXX-XXXXX-XXXXX-XXXXX-XXXXX`.
