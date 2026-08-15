"""Smoke tests for the message-dispatch wiring in main.py.

These drive the real bot object and cog listeners without a Discord
connection: messages are faked and dispatched straight into the event loop.
"""

import asyncio
from collections.abc import AsyncIterator
from typing import cast

import discord
import pytest

import main
from bot import PDEUBot
from cogs.currency import CurrencyCog, ExchangeRateClient
from tests.fakes import WATCH_CHANNEL_ID, FakeChannel, make_message

# The only user ID the NiceCog replies to (see cogs/nice.py).
PATROPOLIS_ID = 444270573434961932

FIXED_RATES = {"EUR": 1.0, "SEK": 10.0, "DKK": 7.5}


class SmokeBot(PDEUBot):
    """PDEUBot without prefix-command processing, which needs a logged-in bot.

    The bot registers no prefix commands, so dropping the handler keeps the
    smoke tests focused on the cog listeners.
    """

    async def on_message(self, message: discord.Message) -> None:
        pass


class StubRateClient:
    """Duck-typed ExchangeRateClient serving fixed rates without network access."""

    async def get_rate_map(self) -> dict[str, float]:
        return dict(FIXED_RATES)

    async def close(self) -> None:
        pass


def get_currency_cog(bot: SmokeBot) -> CurrencyCog:
    """Return the loaded CurrencyCog.

    load_extension re-executes the module instead of using the import cache,
    so the cog's class is not identical to the one imported here and
    isinstance checks fail; the cast is for typing only.
    """
    cog = bot.get_cog("CurrencyCog")
    assert cog is not None
    return cast(CurrencyCog, cog)


@pytest.fixture
async def bot() -> AsyncIterator[SmokeBot]:
    """Bot wired like main() but without a Discord connection."""
    bot = SmokeBot(
        watch_channel_id=WATCH_CHANNEL_ID, command_prefix="!", intents=main.intents
    )
    # dispatch() schedules listeners on bot.loop, which is a sentinel until
    # login; point it at the test's running loop instead.
    bot.loop = asyncio.get_running_loop()
    for cog in main.INITIAL_COGS:
        await bot.load_extension(cog)
    yield bot
    await get_currency_cog(bot).client.close()


async def wait_for_send(channel: FakeChannel) -> None:
    """Wait until the channel's send mock is called, failing on timeout."""
    for _ in range(100):
        if channel.send.called:
            return
        await asyncio.sleep(0.01)
    raise AssertionError("timed out waiting for channel.send")


async def drain_events() -> None:
    """Let every task scheduled by dispatch() run to completion."""
    for _ in range(10):
        await asyncio.sleep(0.01)


async def test_nice_easter_egg(bot: SmokeBot) -> None:
    """A "nice" message from Patropolis in the watched channel gets exactly one
    non-empty reply."""
    message = make_message("nice", author_id=PATROPOLIS_ID)

    bot.dispatch("message", message)

    await wait_for_send(message.channel)
    message.channel.send.assert_called_once()
    reply = message.channel.send.call_args.args[0]
    assert isinstance(reply, str)
    assert reply


async def test_nice_ignores_other_users(bot: SmokeBot) -> None:
    """A "Nice" message from any user other than Patropolis is ignored: the
    listeners run, but no reply is sent."""
    message = make_message("Nice!", author_id=2)

    bot.dispatch("message", message)

    await drain_events()
    message.channel.send.assert_not_called()


async def test_currency_conversion(bot: SmokeBot) -> None:
    """A message mentioning an amount in a supported currency gets a reply
    with the converted values in a code block."""
    cog = get_currency_cog(bot)
    await cog.client.close()
    cog.client = cast(ExchangeRateClient, StubRateClient())

    message = make_message("I spent 100 SEK today")

    bot.dispatch("message", message)

    await wait_for_send(message.channel)
    message.channel.send.assert_called_once()
    sent = message.channel.send.call_args.args[0]
    assert "```100.0 SEK is:" in sent
    assert "10.0 EUR" in sent
    assert "75.0 DKK" in sent
