import asyncio
import re
from typing import Iterable

import httpx
from bs4 import BeautifulSoup

from app.models import ScrapeResult
from app.services.code_store import CodeStore


SHIFT_CODE_PATTERN = re.compile(r"\b[A-Z0-9]{5}(?:-[A-Z0-9]{5}){4}\b")


class ShiftCodeScraper:
    def __init__(self, store: CodeStore, timeout_seconds: float = 15.0) -> None:
        self.store = store
        self.timeout_seconds = timeout_seconds

    async def scrape(self, sources: Iterable[str]) -> ScrapeResult:
        source_list = list(sources)
        html_documents = await self._fetch_sources(source_list)

        found_codes = sorted(
            {
                code
                for html in html_documents
                for code in self.extract_codes(html)
            }
        )

        return await asyncio.to_thread(
            self.store.persist_after_scrape,
            found_codes,
            source_list,
        )

    async def _fetch_sources(self, sources: list[str]) -> list[str]:
        async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=self.timeout_seconds,
            headers={"User-Agent": "shift-code-auto-submitter/0.1"},
        ) as client:
            responses = await asyncio.gather(
                *(client.get(source) for source in sources),
                return_exceptions=True,
            )

        html_documents: list[str] = []
        for response in responses:
            if isinstance(response, Exception):
                continue

            if response.is_success:
                html_documents.append(response.text)

        return html_documents

    @staticmethod
    def extract_codes(raw_html: str) -> list[str]:
        text = BeautifulSoup(raw_html, "html.parser").get_text(" ", strip=True).upper()
        return SHIFT_CODE_PATTERN.findall(text)
