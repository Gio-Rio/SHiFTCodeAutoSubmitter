import asyncio

from app.services.code_store import CodeStateStore
from app.services.scraper import ShiftCodeScraper


def test_extract_codes_from_html():
    html = """
    <html>
      <body>
        <p>Use code abcde-fghij-klmno-pqrst-uvwxy today.</p>
        <p>Ignore this invalid code: ABCD-FGHIJ-KLMNO-PQRST-UVWXY</p>
      </body>
    </html>
    """

    codes = ShiftCodeScraper.extract_codes(html)

    assert codes == ["ABCDE-FGHIJ-KLMNO-PQRST-UVWXY"]


def test_scrape_queues_only_new_codes(tmp_path):
    async def run_test():
        store = CodeStateStore(
            tmp_path / "unsubmitted_codes.json",
            tmp_path / "submitted_codes.json",
        )
        scraper = ShiftCodeScraper(store=store)

        async def fake_fetch_sources(_sources):
            return [
                "<p>ABCDE-FGHIJ-KLMNO-PQRST-UVWXY</p>",
                "<p>ZZZZZ-11111-YYYYY-22222-XXXXX</p>",
            ]

        scraper._fetch_sources = fake_fetch_sources  # type: ignore[method-assign]
        first_result = await scraper.scrape(["https://example.com"])
        second_result = await scraper.scrape(["https://example.com"])

        assert first_result.new_codes == [
            "ABCDE-FGHIJ-KLMNO-PQRST-UVWXY",
            "ZZZZZ-11111-YYYYY-22222-XXXXX",
        ]
        assert first_result.queued_code_count == 2
        assert second_result.new_codes == []
        assert second_result.queued_code_count == 2

    asyncio.run(run_test())
