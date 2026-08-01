"""Project configuration package.

Re-exports the singleton ``settings`` so callers can do
``from config import settings`` without reaching into the module path.
"""

from config.settings import settings

__all__ = ["settings"]
