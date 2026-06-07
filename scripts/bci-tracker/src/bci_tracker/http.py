from __future__ import annotations

import time
from typing import Any, Dict

import requests


class RateLimiter:
    def __init__(self, per_second: float) -> None:
        self.interval = 1.0 / per_second if per_second > 0 else 0.0
        self._last = 0.0

    def wait(self) -> None:
        if self.interval <= 0:
            return
        now = time.monotonic()
        delay = self.interval - (now - self._last)
        if delay > 0:
            time.sleep(delay)
        self._last = time.monotonic()


class HttpClient:
    def __init__(self, cfg: Dict[str, Any]) -> None:
        http_cfg = cfg.get("http", {})
        self.timeout = float(http_cfg.get("timeout_seconds", 30))
        self.max_retries = int(http_cfg.get("max_retries", 3))
        self.rate_limiter = RateLimiter(float(http_cfg.get("rate_limit_per_sec", 3)))
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": http_cfg.get("user_agent", "bci-tracker/0.1")})

    def get(self, url: str, **kwargs: Any) -> requests.Response:
        last_error: Exception | None = None
        for attempt in range(self.max_retries + 1):
            self.rate_limiter.wait()
            try:
                response = self.session.get(url, timeout=self.timeout, **kwargs)
                if response.status_code in {429} or response.status_code >= 500:
                    if attempt < self.max_retries:
                        time.sleep(2 ** attempt)
                        continue
                response.raise_for_status()
                return response
            except requests.RequestException as exc:
                last_error = exc
                if attempt < self.max_retries:
                    time.sleep(2 ** attempt)
                    continue
                raise
        assert last_error is not None
        raise last_error
