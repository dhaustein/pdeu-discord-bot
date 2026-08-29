"""Central dynaconf settings instance for the bot.

Configuration sources, in increasing precedence:

1. ``config/settings.yaml`` — non-secret, version-controlled defaults.
2. ``PDEU_*`` environment variables — secrets and local/CI overrides.

Active environment is selected with ``ENV_FOR_DYNACONF`` (default
``development``); the matching ``[<env>]`` section in ``settings.yaml`` is
applied on top of ``[default]``.
"""

from __future__ import annotations

from pathlib import Path

from dynaconf import Dynaconf

# Project root = parent of this `config/` package.
ROOT_PATH = Path(__file__).resolve().parent.parent

settings = Dynaconf(
    root_path=str(ROOT_PATH),
    envvar_prefix="PDEU",
    settings_files=["config/settings.yaml"],
    environments=True,
    env="development",
    load_dotenv=False,
    lowercase_read=False,
    merge_enabled=True,
)

__all__ = ["settings"]
