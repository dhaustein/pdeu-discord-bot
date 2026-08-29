import asyncio
import logging
import sys

import discord

from bot import PDEUBot
from log_setup import preconfigure_logging, setup_logging

# Phase 1: configure stdout logging before importing `config` (settings are
# loaded during Dynaconf construction in `config.settings`). Level comes from
# PDEU_LOG_LEVEL only; settings aren't loaded yet. setup_logging() below
# finalizes from settings.
preconfigure_logging()

from config import settings

setup_logging()

logger = logging.getLogger(__name__)

# Validate required configuration up front so the bot fails fast with a clear
# message instead of a cryptic Discord error mid-startup.
DISCORD_TOKEN = settings.DISCORD_TOKEN
WATCH_CHANNEL_ID = settings.WATCH_CHANNEL_ID

if not DISCORD_TOKEN:
    sys.exit(
        "DISCORD_TOKEN is not set. Export PDEU_DISCORD_TOKEN. "
        "See README.md → Configuration."
    )
if not WATCH_CHANNEL_ID:
    sys.exit(
        "WATCH_CHANNEL_ID is not set. Put it in config/settings.yaml "
        "or export PDEU_WATCH_CHANNEL_ID. See README.md → Configuration."
    )

# Cogs loaded at startup. Add new feature cogs here (e.g. "cogs.reactions").
# Each entry is a Python module path resolvable from the project root.
INITIAL_COGS = [
    "cogs.nice",
    "cogs.currency",
    # "cogs.example",  # Uncomment to enable the template cog.
]

# Privileged intents: message_content must also be enabled in the
# Discord Developer Portal under Bot > Privileged Gateway Intents.
intents = discord.Intents.default()
intents.message_content = True

# Cogs read the watched channel via `bot.watch_channel_id` in their setup().
bot = PDEUBot(watch_channel_id=WATCH_CHANNEL_ID, command_prefix="!", intents=intents)


@bot.event
async def on_ready() -> None:
    if bot.user is None:
        logger.error("Bot user is None in on_ready event")
        return
    logger.info("Logged in as %s (id: %s)", bot.user, bot.user.id)
    logger.info("Watching channel %s", WATCH_CHANNEL_ID)
    logger.info("Loaded cogs: %s", ", ".join(bot.cogs.keys()) or "(none)")


async def main() -> None:
    async with bot:
        for cog in INITIAL_COGS:
            logger.debug("Loading cog: %s", cog)
            await bot.load_extension(cog)
        await bot.start(DISCORD_TOKEN)


if __name__ == "__main__":
    asyncio.run(main())
