"""Central dynaconf settings instance for the bot.

Configuration sources, in increasing precedence:

1. ``config/settings.yaml`` — non-secret, version-controlled defaults.
2. ``secrets.yaml`` — SOPS + age encrypted secrets (decrypted by our custom
   loader in ``config/sops_loader.py``).
3. ``DYNACONF_*`` / ``PDEU_*`` environment variables — for local overrides
   and CI/deploys where you don't want to re-encrypt just to tweak a value.

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
    # Our SOPS loader runs before the built-in env loader, so env vars still
    # win over secrets. The default core loaders (TOML/YAML/etc.) stay active.
    loaders=[
        "config.sops_loader",
        "dynaconf.loaders.env_loader",
    ],
    load_dotenv=False,
    lowercase_read=False,
    merge_enabled=True,
)

__all__ = ["settings"]
