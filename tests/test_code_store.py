from concurrent.futures import ThreadPoolExecutor, as_completed

from app.models import StoredCodes
from app.services.code_store import CodeStore


def test_code_store_round_trip(tmp_path):
    store = CodeStore(tmp_path / "codes.json")
    payload = StoredCodes(known_codes=["ABCDE-FGHIJ-KLMNO-PQRST-UVWXY"])

    store.save(payload)
    loaded = store.load()

    assert loaded.known_codes == payload.known_codes
    assert loaded.last_scraped_at is None


def test_persist_after_scrape_concurrent_merge(tmp_path):
    """Parallel persist calls must not drop codes when each adds a disjoint key."""
    store = CodeStore(tmp_path / "codes.json")
    n = 32
    sources = ["https://example.com"]

    def run(i: int) -> None:
        code = f"{i:05d}-11111-22222-33333-44444"
        store.persist_after_scrape([code], sources)

    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = [pool.submit(run, i) for i in range(n)]
        for f in as_completed(futures):
            f.result()

    loaded = store.load()
    assert len(loaded.known_codes) == n
    assert set(loaded.known_codes) == {
        f"{i:05d}-11111-22222-33333-44444" for i in range(n)
    }
