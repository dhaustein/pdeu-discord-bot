"""Replies 'hello world' when a trigger phrase appears as a standalone word."""

import logging

import discord

from .base import MessageWatcherCog

logger = logging.getLogger(__name__)

# Trigger phrases: the bot replies "hello world" when any of these appears
# as a standalone word (surrounded by whitespace) in the watched channel.
# Add new phrases to this list to extend the bot's vocabulary.
TRIGGER_PHRASES = ["Nice"]


class HelloWorldCog(MessageWatcherCog):
    """Replies 'hello world' when a trigger phrase appears as a standalone word."""

    async def handle(self, message: discord.Message) -> None:
        # Pad the message with spaces so phrases at the start/end also match.
        padded_content = f" {message.content} "
        for phrase in TRIGGER_PHRASES:
            if f" {phrase} " in padded_content:
                logger.debug("Trigger '%s' matched in message %s", phrase, message.id)
                await message.channel.send("hello world")
                return


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(HelloWorldCog(bot, bot.watch_channel_id))
    logger.info("Loaded cog %s", __name__)
