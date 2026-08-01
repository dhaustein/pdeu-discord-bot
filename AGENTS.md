# AGENTS.md - AI Instructions for this Discord bot project

## Overview
You are an expert Python software engineer and architect.

This repository, **pdeu-discord-bot**, is a Python monorepo for a Discord bot running on the PlayDateEU gaming community Discord server.

It uses `uv` for package management and a `Makefile` for task orchestration.

## Repository Architecture
* **Monorepo Structure:** Managed via `uv` Workspaces.
* **`cogs`**: Cogs help organize code in the discord.py library. A Cog is a class for collection of commands, listeners, and state.
* **`config`**: Dynaconf settings for the bot. Loads config from `settings.yaml` Uses Dynaconf SOPS loader to load secrets from `secrets.yaml`.
* **Python Version**: Defined in `.python-version`.

## Tooling & Commands
Always prefer using the `Makefile` over raw shell commands to ensure the `uv` environment is synced correctly.

| Task | Command |
| :--- | :--- |
| **Sync Environment** | `make install` |
| **Full Linting** | `make lint` (runs ruff and mypy) |
| **Format Code** | `make format` (runs ruff format) |
| **Run Tests** | `make test` |
| **See all Make commands** | `make help` |

## Rules of Engagement
1.  **Dependency Management**: Use `uv`. Do not suggest `pip install`.
2.  **Code Style**:
    * Use **Ruff** for linting and formatting.
    * Use **Mypy** for type checking; all new code must be fully typed. See root `pyproject.toml` for typing rules.
3. **Docstrings**: We use Google style docstrings but without restating types, as that is infered from static typing hints.
4. **Commits**: We use conventional commits, eg. `<type>[optional scope]: <description>`.

### Coding and Typing standards example
BAD:
```python
class GreetingCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def on_message(self, message):
        if "hello" in message.content:
            await message.channel.send("hi")

def get_watched_channel():
    return bot.get_channel(settings.CHANNEL_ID)
```

GOOD:
```python
class GreetingCog(commands.Cog):
    """Replies with a greeting when a user says hello in the watched channel."""

    def __init__(self, bot: commands.Bot, watch_channel_id: int) -> None:
        self.bot = bot
        self.watch_channel_id = watch_channel_id

    async def on_message(self, message: discord.Message) -> None:
        if message.channel.id != self.watch_channel_id:
            return
        if "hello" in message.content.lower():
            await message.channel.send("hi")

def get_watched_channel(bot: commands.Bot, channel_id: int) -> discord.TextChannel | None:
    """Return the watched channel object, or None if not found.

    Args:
        bot: The bot instance to look up the channel from.
        channel_id: The Discord channel ID to resolve.

    Returns:
        The text channel, or None if it could not be resolved.
    """
    return bot.get_channel(channel_id)
```

## Prohibited Actions
* Do not modify the `uv.lock` file manually.
* Do not warn about or reformat current Python exception syntax, we use the Python 3.14+ format (PEP 758) without parentheses.
