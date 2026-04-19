import asyncio
import re
import time
from typing import Iterable

from playwright.async_api import (
    Error as PlaywrightError,
    Locator,
    Page,
    TimeoutError as PlaywrightTimeoutError,
    async_playwright,
)

from app.config import Settings
from app.models import CodeSubmissionOutcome, SubmissionResult, SubmissionStatus


class ShiftCodeSubmitter:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def submit_codes(self, codes: Iterable[str]) -> SubmissionResult:
        code_list = list(codes)
        if not code_list:
            return SubmissionResult(
                attempted_codes=0,
                processed_codes=[],
                remaining_unsubmitted_codes=0,
                login_attempts=0,
                target_game=self.settings.target_game,
                target_platform=self.settings.target_platform_button_text,
            )

        if not self.settings.username or not self.settings.password:
            raise ValueError("USERNAME and PASSWORD must be set in the .env file.")

        login_attempts = 0
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(
                headless=self.settings.headless_browser
            )
            context = await browser.new_context()
            page = await context.new_page()
            try:
                for attempt in range(1, self.settings.login_max_attempts + 1):
                    login_attempts = attempt
                    try:
                        await self._login(page)
                        await self._open_rewards(page)
                        break
                    except (PlaywrightError, PlaywrightTimeoutError):
                        if attempt == self.settings.login_max_attempts:
                            raise
                        await page.goto("about:blank")
                        await asyncio.sleep(1)

                outcomes = await self._submit_each_code(page, code_list)
            finally:
                await context.close()
                await browser.close()

        return SubmissionResult(
            attempted_codes=len(code_list),
            processed_codes=outcomes,
            remaining_unsubmitted_codes=0,
            login_attempts=login_attempts,
            target_game=self.settings.target_game,
            target_platform=self.settings.target_platform_button_text,
        )

    async def _login(self, page: Page) -> None:
        await page.goto(self.settings.shift_home_url, wait_until="domcontentloaded")
        await self._fill_login_form(page)
        await self._submit_login(page)
        await page.wait_for_load_state("networkidle")

    async def _fill_login_form(self, page: Page) -> None:
        email_input = page.locator(
            'input[type="email"], input[name="email"], input[autocomplete="username"]'
        ).first
        password_input = page.locator(
            'input[type="password"], input[name="password"], input[autocomplete="current-password"]'
        ).first

        await email_input.wait_for(state="visible")
        await email_input.fill(self.settings.username or "")
        await password_input.fill(self.settings.password or "")

    async def _submit_login(self, page: Page) -> None:
        login_button = page.get_by_role(
            "button", name=re.compile(r"(sign in|log in|login)", re.IGNORECASE)
        ).first
        if await login_button.count():
            await login_button.click()
            return

        password_input = page.locator(
            'input[type="password"], input[name="password"], input[autocomplete="current-password"]'
        ).first
        await password_input.press("Enter")

    async def _open_rewards(self, page: Page) -> None:
        rewards_target = page.get_by_role("link", name="Rewards").first
        if not await rewards_target.count():
            rewards_target = page.get_by_role("button", name="Rewards").first
        await rewards_target.click()
        await page.get_by_text("Code Redemption", exact=True).wait_for()

    async def _submit_each_code(
        self, page: Page, codes: list[str]
    ) -> list[CodeSubmissionOutcome]:
        outcomes: list[CodeSubmissionOutcome] = []

        for i, code in enumerate(codes):
            if i > 0:
                await asyncio.sleep(self.settings.between_submissions_pause_seconds)

            code_input, check_button, baseline_text = await self._wait_until_check_enabled(
                page, code
            )
            await check_button.click()
            outcome = await self._classify_code(page, code, code_input, baseline_text)
            outcomes.append(outcome)
            if outcome.status == SubmissionStatus.EXPIRED:
                await self._open_rewards(page)

        return outcomes

    async def _wait_until_check_enabled(
        self, page: Page, code: str
    ) -> tuple[Locator, Locator, str]:
        """Re-resolve input and CHECK each poll; wait until CHECK is enabled (SPA often disables it between requests)."""
        deadline = time.monotonic() + self.settings.check_button_ready_timeout_seconds
        interval = self.settings.code_validation_poll_interval_seconds
        while time.monotonic() < deadline:
            code_input = await self._locate_code_input(page)
            await code_input.fill("")
            await code_input.fill(code)
            check_button = page.get_by_role(
                "button", name=self.settings.check_button_text
            ).first
            await check_button.wait_for(state="visible", timeout=5_000)
            if await check_button.is_enabled():
                baseline_text = await page.locator("body").inner_text()
                return code_input, check_button, baseline_text
            await asyncio.sleep(interval)

        raise PlaywrightTimeoutError(
            "Timed out waiting for CHECK to be enabled before submitting the next code."
        )

    async def _locate_code_input(self, page: Page):
        code_redemption = page.get_by_text("Code Redemption", exact=True)
        container = page.locator("section, div").filter(has=code_redemption).first
        candidate = container.locator("input").first
        if await candidate.count():
            await candidate.wait_for(state="visible")
            return candidate

        fallback = page.locator("input").nth(0)
        await fallback.wait_for(state="visible")
        return fallback

    async def _classify_code(
        self,
        page: Page,
        code: str,
        code_input,
        baseline_text: str,
    ) -> CodeSubmissionOutcome:
        invalid_message = page.get_by_text(self.settings.invalid_code_message, exact=False)
        expired_message = page.get_by_text(self.settings.expired_code_message, exact=False)
        platform_message = page.get_by_text(
            self.settings.platform_selection_message, exact=False
        )

        outcome, unsuccessful_detail = await self._wait_for_outcome(
            page,
            code_input,
            invalid_message,
            expired_message,
            platform_message,
            baseline_text,
        )
        if outcome == SubmissionStatus.UNSUCCESSFUL:
            await code_input.fill("")
            return CodeSubmissionOutcome(
                code=code,
                status=SubmissionStatus.UNSUCCESSFUL,
                detail=unsuccessful_detail,
            )

        if outcome == SubmissionStatus.EXPIRED:
            await code_input.fill("")
            return CodeSubmissionOutcome(
                code=code,
                status=SubmissionStatus.EXPIRED,
                detail=unsuccessful_detail,
            )

        if outcome == SubmissionStatus.ALREADY_REDEEMED:
            await code_input.fill("")
            return CodeSubmissionOutcome(
                code=code,
                status=SubmissionStatus.ALREADY_REDEEMED,
                detail="This SHiFT code has already been redeemed",
            )

        redeem_status = await self._redeem_for_target(page, code_input, baseline_text)
        if redeem_status == SubmissionStatus.ALREADY_REDEEMED:
            return CodeSubmissionOutcome(
                code=code,
                status=SubmissionStatus.ALREADY_REDEEMED,
                detail="This SHiFT code has already been redeemed",
            )

        if redeem_status == SubmissionStatus.EXPIRED:
            return CodeSubmissionOutcome(
                code=code,
                status=SubmissionStatus.EXPIRED,
                detail="This SHiFT code has expired",
            )

        return CodeSubmissionOutcome(
            code=code,
            status=SubmissionStatus.SUCCESSFUL,
            detail=self.settings.target_platform_button_text,
        )

    def _outcome_from_body_text(
        self, baseline_lower: str, current_lower: str
    ) -> tuple[SubmissionStatus | None, str | None]:
        """Match known SHiFT strings in full body text; require phrase to be new vs pre-CHECK baseline."""

        def newly_contains(snippet: str) -> bool:
            s = snippet.lower()
            return s in current_lower and s not in baseline_lower

        if newly_contains(self.settings.invalid_code_message):
            return SubmissionStatus.UNSUCCESSFUL, self.settings.invalid_code_message
        if newly_contains(self.settings.expired_code_message):
            return SubmissionStatus.EXPIRED, self.settings.expired_code_message

        for marker in self.settings.already_redeemed_markers:
            if newly_contains(marker):
                return SubmissionStatus.ALREADY_REDEEMED, None

        if newly_contains(self.settings.platform_selection_message):
            return SubmissionStatus.SUCCESSFUL, None
        for fragment in self.settings.platform_selection_markers:
            if newly_contains(fragment):
                return SubmissionStatus.SUCCESSFUL, None

        return None, None

    async def _wait_for_outcome(
        self,
        page: Page,
        code_input,
        invalid_message,
        expired_message,
        platform_message,
        baseline_text: str,
    ) -> tuple[SubmissionStatus, str | None]:
        baseline_lower = baseline_text.lower()
        interval = self.settings.code_validation_poll_interval_seconds
        for _ in range(self.settings.code_validation_max_polls):
            current_lower = (await page.locator("body").inner_text()).lower()
            body_outcome, body_detail = self._outcome_from_body_text(
                baseline_lower, current_lower
            )
            if body_outcome is not None:
                return body_outcome, body_detail

            if await self._input_is_empty(code_input):
                return SubmissionStatus.SUCCESSFUL, None

            # Locator fallbacks when text is present but not picked up by inner_text (e.g. shadow roots).
            current_for_locator = current_lower
            if await invalid_message.count() and await invalid_message.first.is_visible():
                if current_for_locator != baseline_lower:
                    return SubmissionStatus.UNSUCCESSFUL, self.settings.invalid_code_message
            if await expired_message.count() and await expired_message.first.is_visible():
                if current_for_locator != baseline_lower:
                    return SubmissionStatus.UNSUCCESSFUL, self.settings.expired_code_message
            if await platform_message.count() and await platform_message.first.is_visible():
                if current_for_locator != baseline_lower:
                    return SubmissionStatus.SUCCESSFUL, None

            await asyncio.sleep(interval)

        raise PlaywrightTimeoutError("Timed out waiting for code validation outcome.")

    async def _redeem_for_target(
        self, page: Page, code_input, baseline_text: str
    ) -> SubmissionStatus:
        baseline_lower = baseline_text.lower()
        game_heading = page.get_by_text(self.settings.target_game, exact=True).first
        game_container = page.locator("section, div").filter(has=game_heading).first
        target_button = game_container.get_by_role(
            "button", name=self.settings.target_platform_button_text
        ).first
        await target_button.click()

        interval = self.settings.code_validation_poll_interval_seconds
        for _ in range(self.settings.redemption_max_polls):
            if await self._input_is_empty(code_input):
                return SubmissionStatus.SUCCESSFUL
            current_text = (await page.locator("body").inner_text()).lower()
            if any(marker in current_text for marker in self.settings.already_redeemed_markers):
                if current_text != baseline_lower:
                    await code_input.fill("")
                    return SubmissionStatus.ALREADY_REDEEMED
            if self.settings.expired_code_message.lower() in current_text:
                if current_text != baseline_lower:
                    await code_input.fill("")
                    return SubmissionStatus.EXPIRED
            await asyncio.sleep(interval)

        raise PlaywrightTimeoutError("Timed out waiting for redemption to clear the code input.")

    @staticmethod
    async def _input_is_empty(code_input) -> bool:
        value = await code_input.input_value()
        return value.strip() == ""
