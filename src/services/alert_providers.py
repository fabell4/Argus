"""Alert provider implementations (Webhook, Gotify, ntfy, Apprise)."""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from datetime import datetime

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

_LOG = logging.getLogger(__name__)
_DEFAULT_TIMEOUT = 10


def _build_session() -> requests.Session:
    session = requests.Session()
    retry = Retry(total=2, backoff_factor=0.5, status_forcelist=[429, 500, 502, 503, 504])
    session.mount("https://", HTTPAdapter(max_retries=retry))
    session.mount("http://", HTTPAdapter(max_retries=retry))
    return session


class AlertProvider(ABC):
    """Abstract base for alert notification providers."""

    @abstractmethod
    def send_alert(self, failure_count: int, last_error: str, timestamp: datetime) -> None: ...


class WebhookProvider(AlertProvider):
    def __init__(self, url: str, timeout: int = _DEFAULT_TIMEOUT) -> None:
        self._url = url
        self._timeout = timeout
        self._session = _build_session()

    def send_alert(self, failure_count: int, last_error: str, timestamp: datetime) -> None:
        payload = {
            "source": "Argus",
            "failure_count": failure_count,
            "last_error": last_error,
            "timestamp": timestamp.isoformat(),
        }
        resp = self._session.post(self._url, json=payload, timeout=self._timeout)
        resp.raise_for_status()


class GotifyProvider(AlertProvider):
    def __init__(self, url: str, token: str, timeout: int = _DEFAULT_TIMEOUT) -> None:
        self._url = url.rstrip("/")
        self._token = token
        self._timeout = timeout
        self._session = _build_session()

    def send_alert(self, failure_count: int, last_error: str, timestamp: datetime) -> None:
        resp = self._session.post(
            f"{self._url}/message",
            json={
                "title": f"Argus: {failure_count} consecutive poll failures",
                "message": f"{last_error}\n\n{timestamp.isoformat()}",
                "priority": 8,
            },
            headers={"X-Gotify-Key": self._token},
            timeout=self._timeout,
        )
        resp.raise_for_status()


class NtfyProvider(AlertProvider):
    def __init__(self, url: str, topic: str, timeout: int = _DEFAULT_TIMEOUT) -> None:
        self._url = url.rstrip("/")
        self._topic = topic
        self._timeout = timeout
        self._session = _build_session()

    def send_alert(self, failure_count: int, last_error: str, timestamp: datetime) -> None:
        resp = self._session.post(
            f"{self._url}/{self._topic}",
            data=f"Argus: {failure_count} consecutive poll failures\n{last_error}",
            headers={
                "Title": "Argus Alert",
                "Priority": "high",
                "Tags": "warning",
            },
            timeout=self._timeout,
        )
        resp.raise_for_status()


class AppriseProvider(AlertProvider):
    def __init__(self, url: str, timeout: int = _DEFAULT_TIMEOUT) -> None:
        self._url = url
        self._timeout = timeout
        self._session = _build_session()

    def send_alert(self, failure_count: int, last_error: str, timestamp: datetime) -> None:
        resp = self._session.post(
            self._url,
            json={
                "title": "Argus Alert",
                "body": f"{failure_count} consecutive poll failures: {last_error}",
            },
            timeout=self._timeout,
        )
        resp.raise_for_status()
