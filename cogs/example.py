"""Example feature cog showing how to add new message-driven behaviors.

Copy this file, rename the class, and implement `handle` to add a new
feature. Then add the module path (e.g. "cogs.reactions") to INITIAL_COGS
in main.py. No other changes needed.
"""

import logging

import discord

from bot import PDEUBot

from .base import MessageWatcherCog

logger = logging.getLogger(__name__)


class ExampleCog(MessageWatcherCog):
    """Template for new message-watching features."""

    async def handle(self, message: discord.Message) -> None:
        # Replace with your own logic. This example does nothing.
        # Example: react with a wave when someone says "bye".
        if " bye " in f" {message.content} ":
            logger.debug("Saw 'bye' in message %s", message.id)
            await message.channel.send("\U0001f44b")


async def setup(bot: PDEUBot) -> None:
    await bot.add_cog(ExampleCog(bot, bot.watch_channel_id))
    logger.info("Loaded cog %s", __name__)
