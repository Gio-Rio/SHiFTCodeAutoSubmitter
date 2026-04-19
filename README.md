# SHiFTCodeAutoSubmitter

Automatically search the web to find new SHiFT codes, save used keys (both real and non-real) in a JSON file, and eventually submit those keys to Gearbox.

## Current scope

This first pass only covers step 1: scraping the web for new Borderlands SHiFT codes and remembering which codes the app has already seen.

## Stack

- FastAPI
- httpx
- BeautifulSoup
- JSON file persistence

## Endpoints

- `GET /health` returns a simple health status
- `GET /codes` returns the currently known codes from local storage
- `POST /scrape` fetches configured source pages, extracts SHiFT-style codes, stores newly discovered ones, and returns the scrape result

## Local setup

1. Create a virtual environment and activate it.
2. Install dependencies:

```bash
pip install -e ".[dev]"
```

3. Copy `.env.example` to `.env` if you want to override defaults.
4. Run the API:

```bash
uvicorn app.main:app --reload
```

## Notes

- Known codes are stored in `data/discovered_codes.json`.
- The scraper uses a SHiFT code pattern of `XXXXX-XXXXX-XXXXX-XXXXX-XXXXX`.
- Two starter source URLs are configured in `app/config.py` and can be moved into env configuration later if you want.

## Next step

After this, the natural next slice is step 2: submitting newly discovered codes against a Gearbox account using credentials stored in `.env`, then splitting results into `successful_codes` and `unsuccessful_codes`.
