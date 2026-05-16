"""Tests for API key auth and rate limiting."""
from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from src.api.main import app

client = TestClient(app, raise_server_exceptions=False)


def test_no_auth_required_when_key_not_set() -> None:
    with patch("src.config.API_KEY", ""):
        resp = client.post("/api/trigger")
        assert resp.status_code in (200, 202, 409)


def test_missing_key_returns_401() -> None:
    key = "a" * 32
    with patch("src.api.auth.config") as mock_cfg:
        mock_cfg.API_KEY = key
        mock_cfg.RATE_LIMIT_PER_MINUTE = 60
        resp = client.post("/api/trigger")
        assert resp.status_code == 401


def test_wrong_key_returns_403() -> None:
    key = "a" * 32
    with patch("src.api.auth.config") as mock_cfg:
        mock_cfg.API_KEY = key
        mock_cfg.RATE_LIMIT_PER_MINUTE = 60
        resp = client.post("/api/trigger", headers={"X-Api-Key": "b" * 32})
        assert resp.status_code == 403


def test_correct_key_passes() -> None:
    key = "a" * 32
    with patch("src.api.auth.config") as mock_cfg:
        mock_cfg.API_KEY = key
        mock_cfg.RATE_LIMIT_PER_MINUTE = 60
        resp = client.post("/api/trigger", headers={"X-Api-Key": key})
        assert resp.status_code in (200, 202, 409)
