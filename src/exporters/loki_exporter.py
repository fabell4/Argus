"""LokiExporter — ships PowerSnapshot as structured log events to Loki's push API."""

from __future__ import annotations

import json
import logging
from datetime import timezone
from typing import Any
from urllib.parse import urlparse

import requests

from src.models.power_snapshot import PowerSnapshot
from src.exporters.base_exporter import BaseExporter

_LOG = logging.getLogger(__name__)

_LOKI_PUSH_PATH = "/loki/api/v1/push"


class LokiExporter(BaseExporter):
    """Export power snapshots as structured log lines to a Loki HTTP endpoint."""

    def __init__(
        self,
        url: str,
        job_label: str = "argus_power",
        timeout_seconds: float = 5.0,
    ) -> None:
        if not url or not url.strip():
            raise ValueError("Loki URL is required")

        stripped = url.strip()
        parsed = urlparse(stripped)

        if parsed.scheme not in ("http", "https"):
            raise ValueError(
                f"Loki URL must use http or https, got: '{parsed.scheme}'"
            )

        if not parsed.hostname:
            raise ValueError("Loki URL must include a hostname")

        if parsed.username or parsed.password:
            _LOG.warning(
                "Loki URL contains embedded credentials. "
                "Consider using environment variables or a reverse proxy for authentication."
            )

        if timeout_seconds <= 0:
            raise ValueError("Timeout must be positive")

        if not job_label or not job_label.strip():
            raise ValueError("Loki job label cannot be empty")

        self._push_url = self._build_push_url(stripped)
        self._job_label = job_label.strip()
        self._timeout_seconds = timeout_seconds

    @staticmethod
    def _build_push_url(url: str) -> str:
        if url.endswith(_LOKI_PUSH_PATH):
            return url
        if url.endswith("/"):
            return f"{url[:-1]}{_LOKI_PUSH_PATH}"
        return f"{url}{_LOKI_PUSH_PATH}"

    @staticmethod
    def _to_loki_timestamp_ns(snapshot: PowerSnapshot) -> str:
        ts = snapshot.timestamp
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        return str(int(ts.timestamp() * 1_000_000_000))

    def _build_labels(self, snapshot: PowerSnapshot) -> dict[str, str]:
        return {
            "job": self._job_label,
            "device_id": snapshot.device_id,
            "device_type": snapshot.device_type,
        }

    def _build_payload(self, snapshot: PowerSnapshot) -> dict[str, Any]:
        line = json.dumps(
            snapshot.to_dict(), ensure_ascii=False, separators=(",", ":")
        )
        return {
            "streams": [
                {
                    "stream": self._build_labels(snapshot),
                    "values": [[self._to_loki_timestamp_ns(snapshot), line]],
                }
            ]
        }

    def export(self, snapshot: PowerSnapshot) -> None:
        payload = self._build_payload(snapshot)
        body = json.dumps(payload).encode("utf-8")

        try:
            response = requests.post(
                self._push_url,
                data=body,
                headers={"Content-Type": "application/json"},
                timeout=self._timeout_seconds,
            )
        except requests.exceptions.ConnectionError as exc:
            raise RuntimeError(f"Loki push connection error: {exc}") from exc
        except requests.exceptions.Timeout as exc:
            raise RuntimeError(f"Loki push timed out: {exc}") from exc

        if response.status_code >= 300:
            raise RuntimeError(
                f"Loki push failed with status {response.status_code}:"
                f" {response.text[:500]}"
            )
        _LOG.debug("Loki event pushed successfully to %s", self._push_url)
