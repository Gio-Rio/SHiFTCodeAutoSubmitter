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

from app.models import ScrapeResult, StoredCodes


class CodeStore:
    def __init__(self, file_path: Path) -> None:
        self.file_path = file_path
        self._thread_lock = threading.Lock()
        # One FD per store for flock: re-opening the lock file per request can let two
        # threads both take LOCK_EX on Linux (separate open file descriptions).
        self._lock_file_handle: object | None = None
        if fcntl is not None:
            lock_path = file_path.with_name(file_path.name + ".lock")
            lock_path.parent.mkdir(parents=True, exist_ok=True)
            self._lock_file_handle = open(lock_path, "a+", encoding="utf-8")

    def load(self) -> StoredCodes:
        return self._load_impl()

    def save(self, data: StoredCodes) -> None:
        with self._exclusive_lock():
            self._save_impl(data)

    def persist_after_scrape(
        self, found_codes: list[str], source_list: list[str]
    ) -> ScrapeResult:
        """Load, merge `found_codes` into known codes, save — all under one exclusive lock."""
        with self._exclusive_lock():
            stored_codes = self._load_impl()
            known_code_set = set(stored_codes.known_codes)
            new_codes = [code for code in found_codes if code not in known_code_set]
            stored_codes.known_codes = sorted(known_code_set | set(found_codes))
            result = ScrapeResult(
                scanned_sources=source_list,
                found_codes=found_codes,
                new_codes=new_codes,
                known_code_count=len(stored_codes.known_codes),
            )
            stored_codes.last_scraped_at = result.last_scraped_at
            self._save_impl(stored_codes)
            return result

    def _load_impl(self) -> StoredCodes:
        if not self.file_path.exists():
            return StoredCodes()

        with self.file_path.open("r", encoding="utf-8") as file:
            payload = json.load(file)

        return StoredCodes.model_validate(payload)

    def _save_impl(self, data: StoredCodes) -> None:
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        fd, temp_path = tempfile.mkstemp(
            suffix=".tmp",
            prefix=self.file_path.name + ".",
            dir=self.file_path.parent,
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as file:
                json.dump(data.model_dump(mode="json"), file, indent=2)
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

    @contextmanager
    def _exclusive_lock(self) -> Iterator[None]:
        # threading.Lock: same-process threads (flock is not always sufficient across threads).
        # fcntl.flock: separate processes (e.g. multiple uvicorn workers).
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
