import os
import time
import json
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import requests
from bs4 import BeautifulSoup


class BaseScraper:
    """
    Shared utilities for SMITE 2 wiki scrapers.
    - Provides a persistent requests session with polite headers
    - Resilient HTML fetching with basic retries and delay
    - Timestamped JSON saving under a dedicated data directory
    """

    DEFAULT_DELAY_SECONDS: float = 0.7
    DEFAULT_MAX_RETRIES: int = 3

    def __init__(self, base_url: str = "https://wiki.smite2.com/") -> None:
        self.base_url = base_url.rstrip("/") + "/"
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": (
                "smite-chatbot-scraper/1.0 (+https://github.com/;"
                " contact: local-dev)"
            )
        })

    # ---- HTTP helpers ----
    def get(self, url: str, *, delay_seconds: Optional[float] = None, max_retries: Optional[int] = None) -> requests.Response:
        attempt_delay = self.DEFAULT_DELAY_SECONDS if delay_seconds is None else delay_seconds
        retries = self.DEFAULT_MAX_RETRIES if max_retries is None else max_retries

        last_exc: Optional[Exception] = None
        for attempt in range(1, retries + 1):
            try:
                response = self.session.get(url, timeout=25)
                response.raise_for_status()
                if attempt_delay > 0:
                    time.sleep(attempt_delay)
                return response
            except Exception as exc:  # noqa: BLE001 - we log and retry
                last_exc = exc
                if attempt < retries:
                    time.sleep(attempt_delay)
                else:
                    raise
        if last_exc:
            raise last_exc
        raise RuntimeError("Unreachable: get() loop exited without response or exception")

    def get_soup(self, url: str) -> BeautifulSoup:
        response = self.get(url)
        return BeautifulSoup(response.text, "html.parser")

    # ---- File helpers ----
    @staticmethod
    def utc_timestamp_iso() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def ensure_dir(path: str) -> None:
        os.makedirs(path, exist_ok=True)

    @staticmethod
    def default_outdir() -> str:
        ts_folder = datetime.now(timezone.utc).strftime("scrape-%Y%m%d_%H%M%SZ")
        path = os.path.join("data", ts_folder)
        BaseScraper.ensure_dir(path)
        return path

    def save_json(self, data: Any, out_path: str, *, include_timestamp: bool = True, metadata: Optional[Dict[str, Any]] = None) -> None:
        payload: Dict[str, Any]
        if isinstance(data, dict):
            payload = dict(data)
        else:
            # Convert dataclasses or arbitrary objects when possible
            if is_dataclass(data):
                payload = asdict(data)
            else:
                payload = {"data": data}

        if include_timestamp:
            payload["scraped_at"] = self.utc_timestamp_iso()
        if metadata:
            payload.setdefault("metadata", {}).update(metadata)

        self.ensure_dir(os.path.dirname(out_path))
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)


