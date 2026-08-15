"""Unit tests for the currency cog's pure functions and ExchangeRateClient."""

import asyncio
import json
import time
from collections.abc import Callable
from pathlib import Path

import httpx
import pytest

from cogs.currency import (
    MAX_AMOUNT,
    MAX_PAIRS_PER_MESSAGE,
    Conversion,
    ExchangeRate,
    ExchangeRateClient,
    convert_from_message,
    convert_pair,
    extract_pairs,
    parse_rates,
    pretty_print_conversions,
    validate_pair,
)

RATES_PAYLOAD = json.dumps(
    [
        {"date": "2026-08-14", "base": "EUR", "quote": "SEK", "rate": 11.0},
        {"date": "2026-08-14", "base": "EUR", "quote": "DKK", "rate": 7.5},
    ]
)

# Units per 1 EUR, as returned by ExchangeRateClient.get_rate_map.
RATE_MAP = {"EUR": 1.0, "SEK": 10.0, "DKK": 7.5}


def test_parse_rates_preserves_order_and_fields() -> None:
    """A well-formed Frankfurter payload parses into ExchangeRate entries in
    payload order, with each field mapped onto the dataclass."""
    rates = parse_rates(RATES_PAYLOAD)

    assert rates == [
        ExchangeRate(date="2026-08-14", base="EUR", quote="SEK", rate=11.0),
        ExchangeRate(date="2026-08-14", base="EUR", quote="DKK", rate=7.5),
    ]


def test_parse_rates_coerces_field_types() -> None:
    """Non-string dates and integer rates are coerced to str and float, so
    consumers always see consistent dataclass field types."""
    rates = parse_rates(
        '[{"date": 20260814, "base": "EUR", "quote": "SEK", "rate": 11}]'
    )

    assert rates[0].date == "20260814"
    assert rates[0].rate == 11.0
    assert isinstance(rates[0].rate, float)


def test_extract_pairs_finds_amount_currency() -> None:
    """An amount word immediately followed by a supported currency code is
    extracted as one (amount, currency) pair."""
    assert extract_pairs("I paid 100 SEK today", {"SEK"}) == [("100", "SEK")]


def test_extract_pairs_is_case_insensitive() -> None:
    """Lowercase currency codes are recognized and normalized to uppercase."""
    assert extract_pairs("100 sek", {"SEK"}) == [("100", "SEK")]


def test_extract_pairs_ignores_currency_as_first_word() -> None:
    """A currency code at the very start of a message has no preceding word to
    use as the amount, so no pair is extracted."""
    assert extract_pairs("SEK 100", {"SEK"}) == []


def test_extract_pairs_scans_across_newlines() -> None:
    """Newlines are treated as word separators, so pairs on separate lines are
    all found in order of appearance."""
    assert extract_pairs("100 SEK\n200 DKK", {"SEK", "DKK"}) == [
        ("100", "SEK"),
        ("200", "DKK"),
    ]


def test_extract_pairs_caps_at_max_pairs_per_message() -> None:
    """A message containing more pairs than MAX_PAIRS_PER_MESSAGE is truncated
    to the first five pairs."""
    text = " ".join(f"{i} SEK" for i in range(MAX_PAIRS_PER_MESSAGE + 2))

    pairs = extract_pairs(text, {"SEK"})

    assert pairs == [(str(i), "SEK") for i in range(MAX_PAIRS_PER_MESSAGE)]


@pytest.mark.parametrize("amount", ["0", "100", "99.5", str(MAX_AMOUNT - 1)])
def test_validate_pair_accepts_plausible_amounts(amount: str) -> None:
    """Plain integers, decimals, zero, and amounts just below MAX_AMOUNT pass
    validation."""
    assert validate_pair(amount, "SEK")


@pytest.mark.parametrize(
    "amount",
    ["abc", "10.0.5", "-5", "", "1e5", str(MAX_AMOUNT), str(MAX_AMOUNT + 1)],
)
def test_validate_pair_rejects_implausible_amounts(amount: str) -> None:
    """Non-numeric text, malformed decimals, negatives, empty strings,
    scientific notation, and amounts at or above MAX_AMOUNT are rejected."""
    assert not validate_pair(amount, "SEK")


def test_convert_pair_converts_through_eur() -> None:
    """The amount is divided by its currency's EUR rate and multiplied into
    every other supported currency; the source currency is excluded from the
    targets."""
    conversion = convert_pair(100.0, "SEK", RATE_MAP)

    assert conversion.amount == 100.0
    assert conversion.currency == "SEK"
    assert conversion.converted == {"EUR": 10.0, "DKK": 75.0}


def test_convert_from_message_converts_each_valid_pair() -> None:
    """Every valid amount-currency pair in a message yields one Conversion, in
    order of appearance."""
    conversions = convert_from_message("100 SEK and 50 DKK", RATE_MAP)

    assert [(c.amount, c.currency) for c in conversions] == [
        (100.0, "SEK"),
        (50.0, "DKK"),
    ]


def test_convert_from_message_skips_invalid_pairs() -> None:
    """Pairs that fail validation are dropped, so a message with no valid pair
    yields no conversions."""
    assert convert_from_message("abc SEK", RATE_MAP) == []


def test_pretty_print_conversions_formats_code_blocks() -> None:
    """A single conversion renders as one Discord code block listing the
    source amount followed by its converted values."""
    conversions = [
        Conversion(amount=100.0, currency="SEK", converted={"EUR": 10.0, "DKK": 75.0})
    ]

    assert (
        pretty_print_conversions(conversions)
        == "```100.0 SEK is: 10.0 EUR  75.0 DKK```"
    )


def test_pretty_print_conversions_rounds_and_joins_blocks() -> None:
    """Converted values are rounded to two decimals, and multiple conversions
    are joined into one message with newlines between code blocks."""
    conversions = [
        Conversion(amount=1.0, currency="EUR", converted={"SEK": 10.126}),
        Conversion(amount=2.0, currency="EUR", converted={"SEK": 20.0}),
    ]

    assert pretty_print_conversions(conversions) == (
        "```1.0 EUR is: 10.13 SEK```\n```2.0 EUR is: 20.0 SEK```"
    )


Handler = Callable[[httpx.Request], httpx.Response]


async def make_client(
    handler: Handler, cache_path: Path, ttl_seconds: int = 86_400
) -> ExchangeRateClient:
    """Build a client backed by a mock transport and a temporary cache path.

    The client exposes no transport injection point, so the mock transport is
    swapped in after construction; the original HTTP client is closed first so
    it is not abandoned unclosed.
    """
    client = ExchangeRateClient(
        "https://example.test/rates", ttl_seconds=ttl_seconds, cache_path=cache_path
    )
    await client.close()
    client._client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return client


def ok_handler(calls: list[httpx.Request]) -> Handler:
    """Return a handler that records requests and serves RATES_PAYLOAD."""

    def _handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, text=RATES_PAYLOAD)

    return _handler


async def test_get_rates_fetches_once_then_serves_memory_cache(
    tmp_path: Path,
) -> None:
    """The first call fetches rates over HTTP; a second call within the TTL is
    served from the in-memory cache without another request."""
    calls: list[httpx.Request] = []
    client = await make_client(ok_handler(calls), tmp_path / "rates.json")

    first = await client.get_rates()
    second = await client.get_rates()

    assert len(calls) == 1
    assert first is second
    await client.close()


async def test_get_rates_refetches_when_cache_is_stale(tmp_path: Path) -> None:
    """Once the TTL has passed, the next call fetches fresh rates from the
    network again."""
    calls: list[httpx.Request] = []
    client = await make_client(ok_handler(calls), tmp_path / "rates.json", ttl_seconds=60)

    await client.get_rates()
    client._last_fetched -= 61  # push the cache past its TTL
    await client.get_rates()

    assert len(calls) == 2
    await client.close()


async def test_get_rates_serves_stale_cache_when_refresh_fails(
    tmp_path: Path,
) -> None:
    """If the refresh request fails but a stale cache exists, the stale rates
    are served instead of raising an error."""
    calls: list[httpx.Request] = []
    responses = [httpx.Response(200, text=RATES_PAYLOAD), httpx.Response(500)]

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return responses[len(calls) - 1]

    client = await make_client(handler, tmp_path / "rates.json", ttl_seconds=60)
    fresh = await client.get_rates()
    client._last_fetched -= 61  # push the cache past its TTL

    stale = await client.get_rates()

    assert len(calls) == 2
    assert stale is fresh
    await client.close()


async def test_get_rates_raises_when_fetch_fails_without_cache(
    tmp_path: Path,
) -> None:
    """With no cached rates to fall back on, a failed request propagates as
    httpx.HTTPError."""
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500)

    client = await make_client(handler, tmp_path / "rates.json")

    with pytest.raises(httpx.HTTPError):
        await client.get_rates()
    await client.close()


async def test_get_rates_loads_fresh_disc_cache_without_network(
    tmp_path: Path,
) -> None:
    """A fresh disc cache written by a previous client instance is loaded on
    first use, so no network request is made."""
    cache_path = tmp_path / "rates.json"
    calls: list[httpx.Request] = []
    first_client = await make_client(ok_handler(calls), cache_path)
    rates = await first_client.get_rates()
    await first_client.close()
    assert len(calls) == 1

    def fail_handler(request: httpx.Request) -> httpx.Response:
        raise AssertionError("network should not be touched")

    second_client = await make_client(fail_handler, cache_path)

    assert await second_client.get_rates() == rates
    await second_client.close()


async def test_get_rates_refetches_when_disc_cache_is_corrupt(
    tmp_path: Path,
) -> None:
    """An unreadable disc cache is discarded and rates are refetched from the
    network instead."""
    cache_path = tmp_path / "rates.json"
    cache_path.write_text("not json", encoding="utf-8")
    calls: list[httpx.Request] = []
    client = await make_client(ok_handler(calls), cache_path)

    rates = await client.get_rates()

    assert len(calls) == 1
    assert len(rates) == 2
    await client.close()


async def test_get_rate_map_includes_eur_base_rate(tmp_path: Path) -> None:
    """The rate map contains one entry per fetched quote plus EUR pinned at
    1.0, matching the shape convert_pair expects."""
    calls: list[httpx.Request] = []
    client = await make_client(ok_handler(calls), tmp_path / "rates.json")

    assert await client.get_rate_map() == {"SEK": 11.0, "DKK": 7.5, "EUR": 1.0}
    await client.close()


async def test_get_rates_skips_malformed_entries_in_disc_cache(
    tmp_path: Path,
) -> None:
    """A disc cache with a partially malformed rates list still loads: broken
    entries are skipped and the usable ones are served without a refetch."""
    cache_path = tmp_path / "rates.json"
    cache_path.write_text(
        json.dumps(
            {
                "fetched_at": time.time(),
                "rates": [
                    {"date": "2026-08-14", "base": "EUR", "quote": "SEK", "rate": 11.0},
                    {"unexpected": "entry"},
                ],
            }
        ),
        encoding="utf-8",
    )

    def fail_handler(request: httpx.Request) -> httpx.Response:
        raise AssertionError("network should not be touched")

    client = await make_client(fail_handler, cache_path)

    rates = await client.get_rates()

    assert rates == [
        ExchangeRate(date="2026-08-14", base="EUR", quote="SEK", rate=11.0)
    ]
    await client.close()


async def test_get_rates_treats_unreadable_cache_timestamp_as_stale(
    tmp_path: Path,
) -> None:
    """A disc cache without a readable fetched_at keeps its salvaged rates but
    marks them stale, so the first call refetches from the network."""
    cache_path = tmp_path / "rates.json"
    cache_path.write_text(
        json.dumps(
            {
                "rates": [
                    {
                        "date": "2026-08-14",
                        "base": "EUR",
                        "quote": "SEK",
                        "rate": 11.0,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    calls: list[httpx.Request] = []
    client = await make_client(ok_handler(calls), cache_path)

    rates = await client.get_rates()

    assert len(calls) == 1
    assert len(rates) == 2
    await client.close()


async def test_get_rates_fetches_once_for_concurrent_callers(
    tmp_path: Path,
) -> None:
    """Concurrent first calls are serialized by the fetch lock: exactly one
    network fetch serves every caller."""
    calls: list[httpx.Request] = []
    client = await make_client(ok_handler(calls), tmp_path / "rates.json")

    results = await asyncio.gather(*(client.get_rates() for _ in range(5)))

    assert len(calls) == 1
    assert all(result == results[0] for result in results)
    await client.close()
