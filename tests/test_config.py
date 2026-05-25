"""Tests for src/config.py."""

from __future__ import annotations

import pytest
from unittest.mock import patch


def test_validate_passes_with_no_api_key() -> None:
    from src import config

    with patch.object(config, "API_KEY", ""):
        config.validate()


def test_validate_rejects_short_api_key() -> None:
    from src import config

    with (
        patch.object(config, "API_KEY", "short"),
        pytest.raises(ValueError, match="API_KEY"),
    ):
        config.validate()


def test_validate_accepts_32_char_key() -> None:
    from src import config

    with patch.object(config, "API_KEY", "a" * 32):
        config.validate()  # should not raise


def test_validate_rejects_invalid_interval() -> None:
    from src import config

    with patch.object(config, "POLL_INTERVAL_MINUTES", 0), pytest.raises(ValueError):
        config.validate()
