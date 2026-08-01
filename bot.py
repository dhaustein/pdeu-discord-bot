"""Custom Bot subclass carrying shared config for cogs."""

from discord.ext import commands


class PDEUBot(commands.Bot):
    """Discord bot with the watched channel ID attached.

    Cogs read `bot.watch_channel_id` in their `setup()` to know which
    channel to watch.
    """

    def __init__(self, watch_channel_id: int, **kwargs: object) -> None:
        super().__init__(**kwargs)  # type: ignore[arg-type]
        self.watch_channel_id = watch_channel_id
