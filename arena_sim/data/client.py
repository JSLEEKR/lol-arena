"""Async HTTP client with on-disk JSON cache.

CommunityDragon is rate-friendly but ~200+ requests per scrape; we cache to
data/raw/cache/ so re-runs are instant and we don't hammer the CDN.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
from pathlib import Path
from typing import Any

import httpx

log = logging.getLogger(__name__)

CACHE_DIR = Path(__file__).resolve().parents[2] / "data" / "raw" / "cache"


def _cache_path(url: str) -> Path:
    h = hashlib.sha256(url.encode()).hexdigest()[:16]
    return CACHE_DIR / f"{h}.json"


class CDragonClient:
    def __init__(
        self,
        *,
        concurrency: int = 16,
        timeout: float = 30.0,
        use_cache: bool = True,
    ) -> None:
        self._client = httpx.AsyncClient(
            timeout=timeout,
            headers={"User-Agent": "arena-sim/0.1 (+https://github.com/local/arena-sim)"},
            follow_redirects=True,
        )
        self._sem = asyncio.Semaphore(concurrency)
        self._use_cache = use_cache
        CACHE_DIR.mkdir(parents=True, exist_ok=True)

    async def __aenter__(self) -> CDragonClient:
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self._client.aclose()

    async def get_json(self, url: str) -> Any:
        cache_file = _cache_path(url)
        if self._use_cache and cache_file.exists():
            return json.loads(cache_file.read_text())

        async with self._sem:
            for attempt in range(3):
                try:
                    resp = await self._client.get(url)
                    resp.raise_for_status()
                    data = resp.json()
                    if self._use_cache:
                        cache_file.write_text(json.dumps(data))
                    return data
                except (httpx.HTTPError, json.JSONDecodeError) as e:
                    if attempt == 2:
                        log.warning("Giving up on %s after 3 attempts: %s", url, e)
                        raise
                    await asyncio.sleep(0.5 * (attempt + 1))
        raise RuntimeError("unreachable")
