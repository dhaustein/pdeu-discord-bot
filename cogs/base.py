"""Base cog for message-watching features.

Shared guards (ignore bots, channel filter) live here so each feature cog
only implements its own message-handling logic.
"""

import logging

import discord
from discord.ext import commands

logger = logging.getLogger(__name__)


class MessageWatcherCog(commands.Cog):
    """Base class for cogs that react to messages in the watched channel.

    Subclasses implement `handle(message)`. The guards below run for every
    message before dispatch, so each feature cog stays focused on its own
    logic and cannot accidentally react to bots or other channels.
    """

    def __init__(self, bot: commands.Bot, watch_channel_id: int):
        self.bot = bot
        self.watch_channel_id = watch_channel_id

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        # Shared guards — applied to every message before dispatch.
        # 1. Ignore all bots (including ourselves) — prevents feedback loops
        #    and stops the bot from reacting to other bots.
        if message.author.bot:
            logger.debug("Ignoring bot author %s", message.author)
            return
        # 2. Only watch the configured channel.
        if message.channel.id != self.watch_channel_id:
            logger.debug(
                "Message %s outside watched channel %s",
                message.id,
                self.watch_channel_id,
            )
            return
        await self.handle(message)

    async def handle(self, message: discord.Message) -> None:
        """Process a message that passed the shared guards. Override in subclasses."""
        raise NotImplementedError
