"""Pytest configuration.

Importing tests.fakes forces the PDEU_* environment values before any test
module imports main, whose import-time configuration validation would
otherwise exit. pytest imports conftest.py ahead of test modules.
"""

import tests.fakes  # noqa: F401
