"""Alert provider implementations (Webhook, Gotify, ntfy, Apprise)."""

from __future__ import annotations

import ipaddress
import logging
import urllib.parse
from abc import ABC, abstractmethod
from datetime import datetime

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

_LOG = logging.getLogger(__name__)
_DEFAULT_TIMEOUT = 10

# Ordered severity levels for minimum-severity filtering.
_SEVERITY_ORDER: dict[str, int] = {
    "low": 0,
    "medium": 1,
    "high": 2,
    "critical": 3,
}

# Severity → provider-specific priority mappings
_NTFY_PRIORITY: dict[str, str] = {
    "critical": "urgent",
    "high": "high",
    "medium": "default",
    "low": "low",
}
_GOTIFY_PRIORITY: dict[str, int] = {
    "critical": 10,
    "high": 8,
    "medium": 5,
    "low": 3,
}

# Link-local and cloud-metadata IP ranges to block (SSRF guard).
# Private RFC 1918 ranges are intentionally allowed for self-hosted deployments.
_BLOCKED_NETWORKS: list[ipaddress.IPv4Network | ipaddress.IPv6Network] = [
    ipaddress.ip_network("169.254.0.0/16"),  # NOSONAR - IPv4 link-local / AWS metadata
    ipaddress.ip_network("100.64.0.0/10"),  # NOSONAR - RFC 6598 shared address space
    ipaddress.ip_network("fe80::/10"),  # NOSONAR - IPv6 link-local
]
_BLOCKED_HOSTNAMES = frozenset(
    {
        "metadata.google.internal",
        "metadata.internal",
        "::1",  # IPv6 loopback literal
    }
)


def _validate_provider_url(url: str) -> str:
    """Validate a provider URL: must be HTTPS and must not target cloud metadata endpoints.

    Raises ValueError if the URL fails scheme validation or is an SSRF-blocked target.
    Returns the url unchanged if valid.
    """
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "https":
        raise ValueError(
            f"Alert provider URL must use https scheme, got: {parsed.scheme!r}"
        )

    hostname = parsed.hostname or ""
    if hostname.lower() in _BLOCKED_HOSTNAMES:
        raise ValueError(f"Alert provider URL targets a blocked hostname: {hostname!r}")

    # Check if the hostname is a literal IP address in a blocked range.
    # Guard against TypeError when comparing addresses across IP versions.
    try:
        addr = ipaddress.ip_address(hostname)
        for network in _BLOCKED_NETWORKS:
            if addr.version == network.version and addr in network:
                raise ValueError(
                    f"Alert provider URL targets a blocked IP range ({network}): {hostname!r}"
                )
    except ValueError as exc:
        # Re-raise if it was our own blocked-range error
        if "blocked" in str(exc):
            raise
        # Otherwise hostname is not a literal IP address — that's fine
    return url


def _build_session() -> requests.Session:
    session = requests.Session()
    retry = Retry(
        total=2, backoff_factor=0.5, status_forcelist=[429, 500, 502, 503, 504]
    )
    session.mount("https://", HTTPAdapter(max_retries=retry))
    return session


class AlertProvider(ABC):
    """Abstract base for alert notification providers."""

    def __init__(self, min_severity: str = "low") -> None:
        self._min_severity = min_severity.lower()

    def meets_min_severity(self, severity: str) -> bool:
        """Return True if *severity* is at or above this provider's minimum."""
        sev = _SEVERITY_ORDER.get(severity.lower(), 0)
        return sev >= _SEVERITY_ORDER.get(self._min_severity, 0)

    @abstractmethod
    def send_alert(
        self, failure_count: int, last_error: str, timestamp: datetime
    ) -> None:
        """Send a poll-failure alert to this provider."""

    def send_event_alert(
        self,
        _event_type: str,
        _device_id: str,
        message: str,
        severity: str,
        timestamp: datetime,
    ) -> None:
        """Send an alert triggered by a power event.

        Default implementation delegates to send_alert so that subclasses which
        don't override this method still deliver a notification.  Subclasses may
        override to produce richer, severity-aware messages.
        """
        self.send_alert(0, f"[{severity.upper()}] {message}", timestamp)


class WebhookProvider(AlertProvider):
    """Sends alerts to a generic HTTP webhook endpoint."""

    def __init__(
        self, url: str, timeout: int = _DEFAULT_TIMEOUT, min_severity: str = "low"
    ) -> None:
        super().__init__(min_severity)
        self._url = _validate_provider_url(url)
        self._timeout = timeout
        self._session = _build_session()

    def send_alert(
        self, failure_count: int, last_error: str, timestamp: datetime
    ) -> None:
        payload = {
            "source": "Argus",
            "failure_count": failure_count,
            "last_error": last_error,
            "timestamp": timestamp.isoformat(),
        }
        resp = self._session.post(self._url, json=payload, timeout=self._timeout)
        resp.raise_for_status()

    def send_event_alert(
        self,
        event_type: str,
        device_id: str,
        message: str,
        severity: str,
        timestamp: datetime,
    ) -> None:
        payload = {
            "source": "Argus",
            "event_type": event_type,
            "device_id": device_id,
            "message": message,
            "severity": severity,
            "timestamp": timestamp.isoformat(),
        }
        resp = self._session.post(self._url, json=payload, timeout=self._timeout)
        resp.raise_for_status()


class GotifyProvider(AlertProvider):
    """Sends alerts via the Gotify push notification server."""

    def __init__(
        self,
        url: str,
        token: str,
        timeout: int = _DEFAULT_TIMEOUT,
        min_severity: str = "low",
    ) -> None:
        super().__init__(min_severity)
        self._url = _validate_provider_url(url).rstrip("/")
        self._token = token
        self._timeout = timeout
        self._session = _build_session()

    def send_alert(
        self, failure_count: int, last_error: str, timestamp: datetime
    ) -> None:
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

    def send_event_alert(
        self,
        event_type: str,
        device_id: str,
        message: str,
        severity: str,
        timestamp: datetime,
    ) -> None:
        priority = _GOTIFY_PRIORITY.get(severity, 5)
        resp = self._session.post(
            f"{self._url}/message",
            json={
                "title": f"Argus: {message}",
                "message": f"Device: {device_id}\nEvent: {event_type}\n\n{timestamp.isoformat()}",
                "priority": priority,
            },
            headers={"X-Gotify-Key": self._token},
            timeout=self._timeout,
        )
        resp.raise_for_status()


class NtfyProvider(AlertProvider):
    """Sends alerts via the ntfy push notification service."""

    def __init__(
        self,
        url: str,
        topic: str,
        timeout: int = _DEFAULT_TIMEOUT,
        min_severity: str = "low",
    ) -> None:
        super().__init__(min_severity)
        self._url = _validate_provider_url(url).rstrip("/")
        self._topic = topic
        self._timeout = timeout
        self._session = _build_session()

    def send_alert(
        self, failure_count: int, last_error: str, timestamp: datetime
    ) -> None:
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

    def send_event_alert(
        self,
        event_type: str,
        _device_id: str,
        message: str,
        severity: str,
        timestamp: datetime,
    ) -> None:
        ntfy_priority = _NTFY_PRIORITY.get(severity, "default")
        resp = self._session.post(
            f"{self._url}/{self._topic}",
            data=message,
            headers={
                "Title": "Argus Power Alert",
                "Priority": ntfy_priority,
                "Tags": event_type,
            },
            timeout=self._timeout,
        )
        resp.raise_for_status()


class AppriseProvider(AlertProvider):
    """Sends alerts via an Apprise-compatible notification service."""

    def __init__(
        self, url: str, timeout: int = _DEFAULT_TIMEOUT, min_severity: str = "low"
    ) -> None:
        super().__init__(min_severity)
        self._url = _validate_provider_url(url)
        self._timeout = timeout
        self._session = _build_session()

    def send_alert(
        self, failure_count: int, last_error: str, timestamp: datetime
    ) -> None:
        resp = self._session.post(
            self._url,
            json={
                "title": "Argus Alert",
                "body": f"{failure_count} consecutive poll failures: {last_error}",
            },
            timeout=self._timeout,
        )
        resp.raise_for_status()

    def send_event_alert(
        self,
        _event_type: str,
        _device_id: str,
        message: str,
        severity: str,
        timestamp: datetime,
    ) -> None:
        resp = self._session.post(
            self._url,
            json={
                "title": f"Argus Power Alert [{severity.upper()}]",
                "body": message,
            },
            timeout=self._timeout,
        )
        resp.raise_for_status()
