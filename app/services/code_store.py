import json
import os
import tempfile
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

try:
    import fcntl
except ImportError:
    fcntl = None  # type: ignore[assignment, misc]

from app.models import (
    CodeSubmissionOutcome,
    ScrapeResult,
    SubmittedCodes,
    SubmissionResult,
    SubmissionStatus,
    UnsubmittedCodes,
)


class JsonFileStore:
    def __init__(self, file_path: Path) -> None:
        self.file_path = file_path
        self._thread_lock = threading.Lock()
        self._lock_file_handle: object | None = None
        if fcntl is not None:
            lock_path = file_path.with_name(file_path.name + ".lock")
            lock_path.parent.mkdir(parents=True, exist_ok=True)
            self._lock_file_handle = open(lock_path, "a+", encoding="utf-8")

    @contextmanager
    def exclusive_lock(self) -> Iterator[None]:
        with self._thread_lock:
            if fcntl is None:
                yield
                return

            fh = self._lock_file_handle
            assert fh is not None
            fcntl.flock(fh.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(fh.fileno(), fcntl.LOCK_UN)

    def load_json(self) -> dict[str, object]:
        if not self.file_path.exists():
            return {}

        with self.file_path.open("r", encoding="utf-8") as file:
            return json.load(file)

    def save_json(self, payload: dict[str, object]) -> None:
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        fd, temp_path = tempfile.mkstemp(
            suffix=".tmp",
            prefix=self.file_path.name + ".",
            dir=self.file_path.parent,
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as file:
                json.dump(payload, file, indent=2)
                file.write("\n")
                file.flush()
                os.fsync(file.fileno())
            os.replace(temp_path, self.file_path)
        except BaseException:
            try:
                os.unlink(temp_path)
            except OSError:
                pass
            raise


class CodeStateStore:
    def __init__(self, unsubmitted_path: Path, submitted_path: Path) -> None:
        self.unsubmitted_store = JsonFileStore(unsubmitted_path)
        self.submitted_store = JsonFileStore(submitted_path)

    def load_unsubmitted(self) -> UnsubmittedCodes:
        with self.unsubmitted_store.exclusive_lock():
            payload = self.unsubmitted_store.load_json()
            return UnsubmittedCodes.model_validate(payload or {})

    def load_submitted(self) -> SubmittedCodes:
        with self.submitted_store.exclusive_lock():
            payload = self.submitted_store.load_json()
            return SubmittedCodes.model_validate(payload or {})

    def load_state(self) -> dict[str, object]:
        return {
            "unsubmitted": self.load_unsubmitted().model_dump(mode="json"),
            "submitted": self.load_submitted().model_dump(mode="json"),
        }

    def persist_after_scrape(
        self, found_codes: list[str], source_list: list[str]
    ) -> ScrapeResult:
        stores = sorted(
            [self.unsubmitted_store, self.submitted_store],
            key=lambda store: str(store.file_path),
        )
        with stores[0].exclusive_lock():
            with stores[1].exclusive_lock():
                unsubmitted = UnsubmittedCodes.model_validate(
                    self.unsubmitted_store.load_json() or {}
                )
                submitted = SubmittedCodes.model_validate(
                    self.submitted_store.load_json() or {}
                )

                seen_codes = (
                    set(unsubmitted.codes)
                    | set(submitted.successful_codes)
                    | set(submitted.unsuccessful_codes)
                    | set(submitted.already_redeemed_codes)
                )
                new_codes = [code for code in found_codes if code not in seen_codes]
                unsubmitted.codes = sorted(set(unsubmitted.codes) | set(new_codes))
                result = ScrapeResult(
                    scanned_sources=source_list,
                    found_codes=found_codes,
                    new_codes=new_codes,
                    queued_code_count=len(unsubmitted.codes),
                )
                unsubmitted.last_updated_at = result.last_scraped_at
                self.unsubmitted_store.save_json(unsubmitted.model_dump(mode="json"))
                return result

    def persist_submission_results(
        self,
        submission_result: SubmissionResult,
    ) -> SubmissionResult:
        stores = sorted(
            [self.unsubmitted_store, self.submitted_store],
            key=lambda store: str(store.file_path),
        )
        with stores[0].exclusive_lock():
            with stores[1].exclusive_lock():
                unsubmitted = UnsubmittedCodes.model_validate(
                    self.unsubmitted_store.load_json() or {}
                )
                submitted = SubmittedCodes.model_validate(
                    self.submitted_store.load_json() or {}
                )

                processed_codes = {outcome.code for outcome in submission_result.processed_codes}
                unsubmitted.codes = [
                    code for code in unsubmitted.codes if code not in processed_codes
                ]
                unsubmitted.last_updated_at = submission_result.finished_at

                for outcome in submission_result.processed_codes:
                    self._append_outcome(submitted, outcome)

                submitted.last_updated_at = submission_result.finished_at
                self.unsubmitted_store.save_json(unsubmitted.model_dump(mode="json"))
                self.submitted_store.save_json(submitted.model_dump(mode="json"))

                return submission_result.model_copy(
                    update={"remaining_unsubmitted_codes": len(unsubmitted.codes)}
                )

    @staticmethod
    def _append_outcome(submitted: SubmittedCodes, outcome: CodeSubmissionOutcome) -> None:
        status_to_bucket = {
            SubmissionStatus.SUCCESSFUL: submitted.successful_codes,
            SubmissionStatus.UNSUCCESSFUL: submitted.unsuccessful_codes,
            SubmissionStatus.ALREADY_REDEEMED: submitted.already_redeemed_codes,
        }
        bucket = status_to_bucket[outcome.status]
        if outcome.code not in bucket:
            bucket.append(outcome.code)
            bucket.sort()
