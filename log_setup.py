"""Two-phase logging setup for the bot, writing to stdout.

Phase 1 — :func:`preconfigure_logging`: installs a stdout handler on the root
logger using only the ``PDEU_LOG_LEVEL`` environment variable. Must be called
*before* ``from config import settings`` so settings-loaded log lines reach
stdout rather than stderr.

Phase 2 — :func:`setup_logging`: re-applies the handler and sets the
authoritative level from ``settings.LOG_LEVEL`` (the ``PDEU_LOG_LEVEL`` env var
overrides ``log_level`` in ``config/settings.yaml``), and pins the discord.py
logger to INFO so enabling DEBUG for the bot doesn't flood output with gateway
internals.
"""

from __future__ import annotations

import logging
import os
import sys
import typing

DEFAULT_LEVEL: int = logging.INFO
LOG_FORMAT: str = "%(asctime)s %(levelname)-8s %(name)s: %(message)s"
ENV_LEVEL_VAR: str = "PDEU_LOG_LEVEL"
# discord.py is very chatty at DEBUG; default to INFO so enabling DEBUG for the
# bot doesn't drown out bot logs with gateway internals. Override via the
# `discord_log_level` setting (PDEU_DISCORD_LOG_LEVEL env var).
DEFAULT_DISCORD_LEVEL: int = logging.INFO


def _stdout_handler() -> logging.StreamHandler[typing.TextIO]:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(LOG_FORMAT))
    return handler


def _coerce_level(level: str | int | None) -> int:
    """Resolve a level name/value to its numeric logging level.

    Args:
        level: A level name (e.g. ``"DEBUG"``), numeric level, or None.

    Returns:
        The numeric level, falling back to :data:`DEFAULT_LEVEL` if unknown.
    """
    if level is None:
        return DEFAULT_LEVEL
    if isinstance(level, int):
        return level
    coerced = logging.getLevelName(str(level).upper())
    return coerced if isinstance(coerced, int) else DEFAULT_LEVEL


def preconfigure_logging() -> None:
    """Phase 1: stdout logging from the ``PDEU_LOG_LEVEL`` env var only.

    Call before :mod:`config.settings` is imported so settings-initiated log
    lines reach stdout. Settings aren't loaded yet, so the
    level comes solely from the environment (default INFO).
    """
    root = logging.getLogger()
    root.handlers = [_stdout_handler()]
    root.setLevel(_coerce_level(os.environ.get(ENV_LEVEL_VAR)))


def setup_logging() -> None:
    """Phase 2: authoritative levels from settings.

    Re-applies the stdout handler and sets the effective level from
    ``settings.LOG_LEVEL`` (env var overrides ``config/settings.yaml``), and
    the discord.py logger level from ``settings.DISCORD_LOG_LEVEL`` (default
    INFO, independent of the bot's level).
    """
    from config.settings import settings

    root = logging.getLogger()
    root.handlers = [_stdout_handler()]
    root.setLevel(_coerce_level(getattr(settings, "LOG_LEVEL", None)))
    logging.getLogger("discord").setLevel(
        _coerce_level(getattr(settings, "DISCORD_LOG_LEVEL", None))
    )
