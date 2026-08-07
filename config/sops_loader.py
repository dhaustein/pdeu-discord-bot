"""Dynaconf loader that decrypts a SOPS-encrypted secrets file with age.

Registered via the ``loaders=[...]`` kwarg in ``config/settings.py``, it runs
*before* the standard env loader so plain environment variables still win over
secrets — handy for local overrides and CI.

The decrypted file is expected to be a flat YAML mapping of key/value pairs.
Keys are upper-cased on load (``discord_token`` -> ``DISCORD_TOKEN``) and the
``sops:`` metadata block that SOPS injects on encryption is stripped.
"""

from __future__ import annotations

import logging
from typing import Any

import yaml
from dynaconf import LazySettings
from dynaconf.loaders.base import SourceMetadata
from dynaconf.utils.parse_conf import parse_conf_data

logger = logging.getLogger(__name__)

DEFAULT_SECRETS_FILE = "secrets.yaml"


def _run_sops_decrypt(path: str) -> tuple[bytes, bytes, int]:
    """Invoke ``sops -d`` on *path* and return (stdout, stderr, returncode)."""
    import subprocess

    proc = subprocess.run(
        ["sops", "-d", path],
        capture_output=True,
        check=False,
    )
    return proc.stdout, proc.stderr, proc.returncode


def load(
    obj: LazySettings,
    env: str = "DEVELOPMENT",
    silent: bool = True,
    key: str | None = None,
    filename: str | None = None,
) -> None:
    """Decrypt *filename* (or ``secrets.yaml``) and merge it into *obj*.

    Mirrors the dynaconf custom-loader contract: ``obj`` is the settings
    instance, ``env`` the active environment, ``silent`` suppresses hard
    failures when True (the default for non-core loaders).
    """
    secrets_path = obj.find_file(filename or DEFAULT_SECRETS_FILE)
    if not secrets_path:
        if not silent:
            raise FileNotFoundError(
                f"SOPS secrets file '{filename or DEFAULT_SECRETS_FILE}' not found"
            )
        logger.debug(
            "SOPS secrets file '%s' not found; skipping secrets load.",
            filename or DEFAULT_SECRETS_FILE,
        )
        return

    stdout, stderr, rc = _run_sops_decrypt(str(secrets_path))
    if rc != 0:
        message = (
            stderr.decode("utf-8", errors="replace").strip() or f"sops exited {rc}"
        )
        if not silent:
            raise RuntimeError(f"sops -d failed for {secrets_path}: {message}")
        logger.warning("SOPS decryption of %s failed: %s", secrets_path, message)
        return

    try:
        raw_data = yaml.safe_load(stdout)
        data: dict[str, Any] = raw_data if isinstance(raw_data, dict) else {}
    except yaml.YAMLError as exc:
        if not silent:
            raise
        logger.warning("Failed to parse decrypted YAML from %s: %s", secrets_path, exc)
        return

    source_metadata = SourceMetadata(
        loader="sops", identifier=str(secrets_path), env=env, merged=False
    )

    # SOPS injects a `sops:` metadata key into every encrypted file; drop it so
    # it doesn't surface as a setting.
    data.pop("sops", None)

    # dynaconf stores keys upper-cased; parse_conf_data coerces strings to the
    # appropriate Python type (ints, bools, etc.), matching how the standard
    # loaders treat values from settings files.
    decoded = {str(k).upper(): parse_conf_data(v) for k, v in data.items()}

    if key:
        value = decoded.get(key.upper())
        if value is not None:
            obj.set(key, value, loader_identifier=source_metadata)
    else:
        obj.update(decoded, loader_identifier=source_metadata)

    obj._loaded_files.append(str(secrets_path))
