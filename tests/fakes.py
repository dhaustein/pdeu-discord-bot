"""Fake Discord objects and environment defaults for tests."""

import os
from dataclasses import dataclass, field
from unittest.mock import AsyncMock

# main.py validates required configuration at import time and exits when it is
# missing. Tests are hermetic: placeholder values are forced (not defaulted) so
# real secrets or channel IDs from the environment never leak into a test run.
# conftest.py imports this module before any test module.
WATCH_CHANNEL_ID = 1234567890  # placeholder, not the real channel

os.environ["PDEU_DISCORD_TOKEN"] = "test-token"
os.environ["PDEU_WATCH_CHANNEL_ID"] = str(WATCH_CHANNEL_ID)


@dataclass
class FakeAuthor:
    """Minimal stand-in for discord.User/Member."""

    id: int
    bot: bool = False


@dataclass
class FakeChannel:
    """Minimal stand-in for discord.TextChannel capturing sent messages."""

    id: int = WATCH_CHANNEL_ID
    send: AsyncMock = field(default_factory=AsyncMock)


@dataclass
class FakeMessage:
    """Duck-typed discord.Message carrying only the attributes cogs read."""

    content: str
    author: FakeAuthor
    channel: FakeChannel
    id: int = 1


def make_message(
    content: str,
    *,
    author_id: int = 1,
    author_bot: bool = False,
    channel_id: int = WATCH_CHANNEL_ID,
) -> FakeMessage:
    """Build a fake message that passes the MessageWatcherCog guards by default.

    Args:
        content: The message text.
        author_id: ID of the message author.
        author_bot: Whether the author is a bot (guards ignore bot authors).
        channel_id: Channel the message was posted in.

    Returns:
        A fake message processable by the cogs.
    """
    return FakeMessage(
        content=content,
        author=FakeAuthor(id=author_id, bot=author_bot),
        channel=FakeChannel(id=channel_id),
    )
