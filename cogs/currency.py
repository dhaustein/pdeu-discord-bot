from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from dataclasses import dataclass
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)

DEFAULT_CACHE_PATH = Path("data/exchange_rates.json")


@dataclass
class ExchangeRate:
    """A single exchange rate quote for a currency pair on a given date."""

    date: str
    base: str
    quote: str
    rate: float


def parse_ndjson(raw: str) -> list[ExchangeRate]:
    """Parse newline-delimited JSON into a list of exchange rates.

    Blank lines are skipped.

    Args:
        raw: The raw NDJSON payload, one JSON object per line.

    Returns:
        The parsed exchange rates, in the order they appear in the payload.
    """
    rates: list[ExchangeRate] = []
    for line in raw.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        obj = json.loads(stripped)
        rates.append(
            ExchangeRate(
                date=obj["date"],
                base=obj["base"],
                quote=obj["quote"],
                rate=float(obj["rate"]),
            )
        )
    return rates


class ExchangeRateClient:
    """Fetches exchange rates from a remote endpoint and caches them on disc for a TTL.

    The cache is persisted as JSON at ``cache_path`` so it survives process and
    container restarts. A stale or missing cache triggers a refetch.
    """

    def __init__(
        self,
        url: str,
        ttl_seconds: int = 86_400,  # TTL 24 hours
        cache_path: Path = DEFAULT_CACHE_PATH,
    ) -> None:
        """Initialize the client.

        Args:
            url: The endpoint returning NDJSON exchange rate data.
            ttl_seconds: How long cached rates are considered fresh before refetching.
            cache_path: Path of the JSON file used to persist the cache across restarts.
        """
        self._url = url
        self._ttl = ttl_seconds
        self._cache_path = cache_path
        self._client = httpx.AsyncClient(
            timeout=10.0,
            transport=httpx.AsyncHTTPTransport(retries=3),
        )
        self._cache: list[ExchangeRate] | None = None
        self._last_fetched: float = 0.0

    @property
    def _is_stale(self) -> bool:
        """Whether the cache has exceeded its TTL and needs refreshing."""
        return (time.time() - self._last_fetched) > self._ttl

    def _load_from_disc(self) -> bool:
        """Populate the in-memory cache from the on-disc cache file, if present.

        Returns:
            True if a usable cache was loaded, False otherwise.
        """
        try:
            payload = json.loads(self._cache_path.read_text(encoding="utf-8"))
        except OSError:
            logger.exception(
                f"Failed to read exchange rate cache from {self._cache_path}"
            )
            return False
        except json.JSONDecodeError:
            logger.warning(
                f"Exchange rate cache at {self._cache_path} is corrupt; will refetch"
            )
            return False
        rates = [ExchangeRate(**entry) for entry in payload["rates"]]
        self._cache = rates
        self._last_fetched = float(payload["fetched_at"])
        logger.info(
            f"Loaded {len(rates)} exchange rates from disc cache at {self._cache_path}"
        )
        return True

    def _save_to_disc(self) -> None:
        """Write the current in-memory cache to the on-disc cache file.

        Writes via a temporary file and atomic rename so a crash mid-write
        cannot leave a corrupt cache behind.
        """
        if self._cache is None:
            logger.debug("Skipping disc cache write: no rates in memory")
            return
        payload = {
            "fetched_at": self._last_fetched,
            "rates": [vars(rate) for rate in self._cache],
        }
        self._cache_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = self._cache_path.with_suffix(self._cache_path.suffix + ".tmp")

        # Write to temporary file
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(payload, f)
            f.flush()
            os.fsync(f.fileno())

        os.replace(tmp_path, self._cache_path)

        logger.debug(
            f"Saved {len(self._cache)} exchange rates to disc cache at {self._cache_path}"
        )

    async def get_rates(self) -> list[ExchangeRate]:
        """Return exchange rates, fetching from the network only when the cache is stale.

        On first use the cache is loaded from disc, so a fresh cache survives
        process and container restarts.

        Returns:
            The cached rates if still fresh, otherwise freshly fetched and parsed rates.

        Raises:
            httpx.HTTPStatusError: If the remote endpoint responds with an error status.
        """
        if self._cache is None:
            self._load_from_disc()

        if not self._is_stale and self._cache is not None:
            logger.debug(
                f"Serving {len(self._cache)} cached exchange rates (fresh for another {self._ttl - (time.time() - self._last_fetched):.0f}s)"
            )
            return self._cache

        logger.debug(
            f"Exchange rate cache is stale or missing; fetching from {self._url}"
        )
        resp = await self._client.get(self._url)
        try:
            resp.raise_for_status()
        except httpx.HTTPStatusError:
            logger.exception(
                f"Exchange rate request to {self._url} failed with status {resp.status_code}"
            )
            raise
        logger.info(f"Received exchange rate API response: {resp.text}")
        self._cache = parse_ndjson(resp.text)
        self._last_fetched = time.time()
        self._save_to_disc()
        return self._cache

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        logger.debug("Closing exchange rate HTTP client")
        await self._client.aclose()


async def main() -> None:
    client = ExchangeRateClient(
        "https://api.frankfurter.dev/v2/rates?quotes=SEK,DKK,CZK,GBP,AUD,EUR"
    )
    try:
        rates = await client.get_rates()  # first fetch is from network or disc cache
        logger.info(f"Loaded {len(rates)} rates")

        rates = await client.get_rates()
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
