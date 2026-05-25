"""Tests for LokiExporter — URL validation, payload shape, optional retry."""
from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
import requests

from src.exporters.loki_exporter import LokiExporter
from src.models.power_snapshot import PowerSnapshot


def _snap(**kwargs: object) -> PowerSnapshot:
    defaults: dict[str, object] = {
        "timestamp": datetime.now(timezone.utc),
        "device_id": "nut:ups@localhost",
        "device_type": "ups",
        "power_watts": 150.0,
        "load_percent": 30.0,
        "battery_percent": 95.0,
    }
    defaults.update(kwargs)
    return PowerSnapshot(**defaults)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# URL validation
# ---------------------------------------------------------------------------

def test_empty_url_raises() -> None:
    with pytest.raises(ValueError, match="required"):
        LokiExporter(url="")


def test_whitespace_url_raises() -> None:
    with pytest.raises(ValueError, match="required"):
        LokiExporter(url="   ")


def test_non_http_scheme_raises() -> None:
    with pytest.raises(ValueError, match="http or https"):
        LokiExporter(url="ftp://loki.example.com")


def test_no_hostname_raises() -> None:
    with pytest.raises(ValueError):
        LokiExporter(url="http://")


def test_zero_timeout_raises() -> None:
    with pytest.raises(ValueError, match="Timeout"):
        LokiExporter(url="http://loki.example.com", timeout_seconds=0)


def test_negative_timeout_raises() -> None:
    with pytest.raises(ValueError, match="Timeout"):
        LokiExporter(url="http://loki.example.com", timeout_seconds=-1)


def test_empty_job_label_raises() -> None:
    with pytest.raises(ValueError, match="job label"):
        LokiExporter(url="http://loki.example.com", job_label="")


def test_valid_http_url_accepted() -> None:
    exporter = LokiExporter(url="http://loki.example.com")
    assert "loki" in exporter._push_url


def test_valid_https_url_accepted() -> None:
    exporter = LokiExporter(url="https://loki.example.com")
    assert "loki" in exporter._push_url


# ---------------------------------------------------------------------------
# Push URL construction
# ---------------------------------------------------------------------------

def test_push_url_appends_path_when_missing() -> None:
    exporter = LokiExporter(url="http://loki.example.com")
    assert exporter._push_url.endswith("/loki/api/v1/push")


def test_push_url_no_double_path_when_already_present() -> None:
    exporter = LokiExporter(url="http://loki.example.com/loki/api/v1/push")
    assert exporter._push_url.count("/loki/api/v1/push") == 1


def test_push_url_handles_trailing_slash() -> None:
    exporter = LokiExporter(url="http://loki.example.com/")
    assert exporter._push_url.endswith("/loki/api/v1/push")
    assert "//" not in exporter._push_url.replace("http://", "")


# ---------------------------------------------------------------------------
# Payload shape
# ---------------------------------------------------------------------------

def _ok_response() -> MagicMock:
    mock_resp = MagicMock()
    mock_resp.status_code = 204
    mock_resp.raise_for_status = MagicMock()
    return mock_resp


def _error_response(status: int = 500) -> MagicMock:
    mock_resp = MagicMock()
    mock_resp.status_code = status
    mock_resp.raise_for_status.side_effect = requests.HTTPError(f"{status} Error")
    return mock_resp


def test_export_posts_to_push_url() -> None:
    exporter = LokiExporter(url="https://loki.example.com")
    with patch("src.exporters.loki_exporter.requests.post", return_value=_ok_response()) as mock_post:
        exporter.export(_snap())
        mock_post.assert_called_once()
        url_called = mock_post.call_args.args[0]
        assert "/loki/api/v1/push" in url_called


def test_export_payload_contains_streams() -> None:
    exporter = LokiExporter(url="https://loki.example.com")
    with patch("src.exporters.loki_exporter.requests.post", return_value=_ok_response()) as mock_post:
        exporter.export(_snap())
        payload = mock_post.call_args.kwargs.get("json") or mock_post.call_args[1].get("json")
        if payload is None:
            # data= kwarg: the body was JSON-encoded bytes
            body_bytes = mock_post.call_args.kwargs.get("data") or mock_post.call_args[1].get("data")
            import json as _json
            payload = _json.loads(body_bytes)
        assert "streams" in payload
        assert len(payload["streams"]) == 1


def test_export_payload_labels_include_job_and_device() -> None:
    exporter = LokiExporter(url="https://loki.example.com", job_label="argus_test")
    with patch("src.exporters.loki_exporter.requests.post", return_value=_ok_response()) as mock_post:
        exporter.export(_snap(device_id="dev-1"))
        import json as _json
        body_bytes = mock_post.call_args.kwargs.get("data") or mock_post.call_args[1].get("data")
        payload = _json.loads(body_bytes)
        labels = payload["streams"][0]["stream"]
        assert labels["job"] == "argus_test"
        assert labels["device_id"] == "dev-1"


def test_export_payload_values_are_non_empty() -> None:
    exporter = LokiExporter(url="https://loki.example.com")
    with patch("src.exporters.loki_exporter.requests.post", return_value=_ok_response()) as mock_post:
        exporter.export(_snap())
        import json as _json
        body_bytes = mock_post.call_args.kwargs.get("data") or mock_post.call_args[1].get("data")
        payload = _json.loads(body_bytes)
        values = payload["streams"][0]["values"]
        assert len(values) >= 1
        ts_ns, log_line = values[0]
        assert int(ts_ns) > 0
        assert len(log_line) > 0


def test_export_raises_on_http_error() -> None:
    exporter = LokiExporter(url="https://loki.example.com")
    with patch("src.exporters.loki_exporter.requests.post", return_value=_error_response(500)):
        with pytest.raises((requests.HTTPError, RuntimeError)):
            exporter.export(_snap())
