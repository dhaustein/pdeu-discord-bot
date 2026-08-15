from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from dataclasses import dataclass
from itertools import islice
from pathlib import Path

import discord
import httpx

from bot import PDEUBot

from .base import MessageWatcherCog

logger = logging.getLogger(__name__)

DEFAULT_CACHE_PATH = Path("data/exchange_rates.json")
EXCHANGE_RATES_URL = (
    "https://api.frankfurter.dev/v2/rates?quotes=SEK,DKK,CZK,GBP,AUD,EUR"
)
# Currency codes recognized in messages; must match the quotes in EXCHANGE_RATES_URL plus EUR.
SUPPORTED_CURRENCIES: set[str] = {"SEK", "DKK", "CZK", "GBP", "AUD", "EUR"}

# Hard limit on how many amount-currency pairs are converted per message.
MAX_PAIRS_PER_MESSAGE = 5
# Amounts at or above this value are rejected as unreasonable.
MAX_AMOUNT = 100_000_000


@dataclass
class ExchangeRate:
    """A single exchange rate quote for a currency pair on a given date."""

    date: str
    base: str
    quote: str
    rate: float


@dataclass
class Conversion:
    """A validated amount in one currency converted to the other supported currencies."""

    amount: float
    currency: str
    converted: dict[str, float]


def parse_rates(raw: str) -> list[ExchangeRate]:
    """Parse exchange rates from a JSON array payload.

    The Frankfurter v2 API returns a JSON array of rate objects.

    Args:
        raw: The raw JSON array payload.

    Returns:
        The parsed exchange rates, in the order they appear in the payload.
    """
    objects: list[dict[str, str | float]] = json.loads(raw)
    return [
        ExchangeRate(
            date=str(obj["date"]),
            base=str(obj["base"]),
            quote=str(obj["quote"]),
            rate=float(obj["rate"]),
        )
        for obj in objects
    ]


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
            url: The endpoint returning exchange rate data.
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
        self._fetch_lock = asyncio.Lock()

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
        try:
            rates = [ExchangeRate(**entry) for entry in payload["rates"]]
            fetched_at = float(payload["fetched_at"])
        except (TypeError, KeyError, ValueError):
            logger.warning(
                f"Exchange rate cache at {self._cache_path} has an unexpected shape; will refetch"
            )
            return False
        self._cache = rates
        self._last_fetched = fetched_at
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
        process and container restarts. Refetches are serialized: concurrent
        callers trigger exactly one network fetch. If a refresh fails and a
        stale cache exists, the stale cache is served instead of raising, and
        the next call retries the fetch.

        Returns:
            The cached rates if fresh, the stale cache if a refresh failed,
            otherwise freshly fetched and parsed rates.

        Raises:
            httpx.HTTPError: If the remote endpoint fails and no cached rates
                are available.
        """
        if self._cache is None:
            self._load_from_disc()

        if not self._is_stale and self._cache is not None:
            logger.debug(
                f"Serving {len(self._cache)} cached exchange rates (fresh for another {self._ttl - (time.time() - self._last_fetched):.0f}s)"
            )
            return self._cache

        async with self._fetch_lock:
            # Re-check under the lock: a coroutine ahead of us may have
            # already refreshed the cache while we waited.
            if not self._is_stale and self._cache is not None:
                logger.debug(
                    f"Serving {len(self._cache)} cached exchange rates refreshed while waiting for the fetch lock"
                )
                return self._cache

            logger.debug(
                f"Exchange rate cache is stale or missing; fetching from {self._url}"
            )
            try:
                resp = await self._client.get(self._url)
                resp.raise_for_status()
            except httpx.HTTPError as exc:
                if self._cache is not None:
                    logger.warning(
                        f"Exchange rate refresh from {self._url} failed ({exc}); serving {len(self._cache)} stale cached rates"
                    )
                    return self._cache
                logger.exception(
                    f"Exchange rate request to {self._url} failed and no cached rates are available"
                )
                raise
            logger.info(f"Received exchange rate API response: {resp.text}")
            self._cache = parse_rates(resp.text)
            self._last_fetched = time.time()
            self._save_to_disc()
            return self._cache

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        logger.debug("Closing exchange rate HTTP client")
        await self._client.aclose()

    async def get_rate_map(self) -> dict[str, float]:
        """Return a mapping of quote currency code to its rate against the base currency.

        The base currency of the fetched quotes is assumed to be EUR and is
        added with a rate of 1.0.

        Returns:
            Mapping of currency code (e.g. "SEK") to units per 1 EUR.
        """
        rates = await self.get_rates()
        rate_map = {rate.quote: rate.rate for rate in rates}
        rate_map["EUR"] = 1.0
        return rate_map


def extract_pairs(text: str, supported_currencies: set[str]) -> list[tuple[str, str]]:
    """Extract amount-currency pairs from a message.

    A pair is any word that exactly matches a supported currency code,
    preceded by another word treated as the amount. Pairs are limited to
    ``MAX_PAIRS_PER_MESSAGE``.

    Args:
        text: The message content to scan.
        supported_currencies: Currency codes that are recognized.

    Returns:
        A list of ``(amount, currency)`` tuples in order of appearance.
    """
    words = text.replace("\n", " ").split()
    pairs: list[tuple[str, str]] = []
    for index, word in enumerate(words):
        if index == 0:
            continue
        if word.upper() in supported_currencies:
            pairs.append((words[index - 1], word.upper()))
    if pairs:
        logger.debug("Currency pairs found: %s", pairs)
    return list(islice(pairs, 0, MAX_PAIRS_PER_MESSAGE))


def validate_pair(amount: str, currency: str) -> bool:
    """Check that an amount-currency pair is a plausible conversion request.

    The amount must be a non-negative number below ``MAX_AMOUNT``.

    Args:
        amount: The raw amount string from the message.
        currency: The currency code following the amount.

    Returns:
        True if the pair passes all checks, False otherwise.
    """
    if not amount.replace(".", "", 1).isdigit():
        logger.debug("Validation failed, not a number: %s %s", amount, currency)
        return False
    if float(amount) >= MAX_AMOUNT:
        logger.debug("Validation failed, amount too large: %s %s", amount, currency)
        return False
    return True


def convert_pair(
    amount: float, currency: str, rate_map: dict[str, float]
) -> Conversion:
    """Convert an amount in one currency into all other supported currencies.

    Conversion goes through EUR: the amount is divided by its currency's
    EUR rate, then multiplied by each other currency's rate.

    Args:
        amount: The validated amount.
        currency: The currency code the amount is denominated in.
        rate_map: Mapping of currency code to units per 1 EUR.

    Returns:
        The conversion result, excluding the original currency from the targets.
    """
    in_eur = amount / rate_map[currency]
    converted = {
        code: in_eur * rate for code, rate in rate_map.items() if code != currency
    }
    return Conversion(amount=amount, currency=currency, converted=converted)


def convert_from_message(text: str, rate_map: dict[str, float]) -> list[Conversion]:
    """Find, validate, and convert all currency amounts mentioned in a message.

    Args:
        text: The message content to scan.
        rate_map: Mapping of currency code to units per 1 EUR.

    Returns:
        One conversion per valid amount-currency pair found.
    """
    conversions: list[Conversion] = []
    for amount_str, currency in extract_pairs(text, set(rate_map)):
        if validate_pair(amount_str, currency):
            conversions.append(convert_pair(float(amount_str), currency, rate_map))
    return conversions


def pretty_print_conversions(conversions: list[Conversion]) -> str:
    """Build a Discord message listing each amount and its converted values.

    Each conversion is wrapped in a code block, e.g.
    ```100 SEK is: 8.75 EUR  76.06 DKK  ...```

    Args:
        conversions: The conversions to render.

    Returns:
        The formatted message string.
    """
    blocks: list[str] = []
    for conv in conversions:
        parts = [f"{round(value, 2)} {code}" for code, value in conv.converted.items()]
        block = f"{round(conv.amount, 2)} {conv.currency} is: " + "  ".join(parts)
        blocks.append(f"```{block}```")
    return "\n".join(blocks)


class CurrencyCog(MessageWatcherCog):
    """Watches the channel for messages mentioning currency amounts and replies with conversions."""

    def __init__(
        self, bot: PDEUBot, watch_channel_id: int, client: ExchangeRateClient
    ) -> None:
        super().__init__(bot, watch_channel_id)
        self.client = client

    async def handle(self, message: discord.Message) -> None:
        # Scan for currency mentions before touching the rate cache or network.
        if not extract_pairs(message.content, SUPPORTED_CURRENCIES):
            return
        rate_map = await self.client.get_rate_map()
        conversions = convert_from_message(message.content, rate_map)
        if not conversions:
            return
        logger.debug(
            "Converting %d currency pair(s) from message %s",
            len(conversions),
            message.id,
        )
        await message.channel.send(pretty_print_conversions(conversions))

    async def cog_unload(self) -> None:
        await self.client.close()


async def setup(bot: PDEUBot) -> None:
    await bot.add_cog(
        CurrencyCog(bot, bot.watch_channel_id, ExchangeRateClient(EXCHANGE_RATES_URL))
    )
    logger.info("Loaded cog %s", __name__)


async def main() -> None:
    client = ExchangeRateClient(EXCHANGE_RATES_URL)
    try:
        rates = await client.get_rates()  # first fetch is from network or disc cache
        logger.info(f"Loaded {len(rates)} rates")

        rates = await client.get_rates()
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
