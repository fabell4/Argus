"""Tests for alert provider implementations and SSRF/URL validation."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
import requests

from src.services.alert_providers import (
    AppriseProvider,
    GotifyProvider,
    NtfyProvider,
    WebhookProvider,
    _validate_provider_url,
)


def _ts() -> datetime:
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# URL validation / SSRF guard
# ---------------------------------------------------------------------------


class TestValidateProviderUrl:
    """Tests for _validate_provider_url SSRF guard and scheme enforcement."""

    def test_https_public_accepted(self) -> None:
        """Public HTTPS URLs are accepted unchanged."""
        assert (
            _validate_provider_url("https://gotify.example.com")
            == "https://gotify.example.com"
        )

    def test_http_public_rejected(self) -> None:
        """Public HTTP URLs are rejected to enforce encrypted transport."""
        with pytest.raises(ValueError, match="https"):
            _validate_provider_url("http://ntfy.example.com")

    def test_https_private_rfc1918_accepted(self) -> None:
        """Private IP ranges are allowed for self-hosted deployments (over HTTPS)."""
        assert _validate_provider_url("https://192.168.1.50:8080/message")  # NOSONAR
        assert _validate_provider_url("https://10.0.0.1:8080")  # NOSONAR
        assert _validate_provider_url("https://172.16.0.1")  # NOSONAR

    def test_link_local_metadata_blocked(self) -> None:
        """Link-local cloud metadata endpoint is blocked."""
        with pytest.raises(ValueError, match="blocked"):
            _validate_provider_url(
                "https://169.254.169.254/latest/meta-data/"
            )  # NOSONAR

    def test_link_local_range_blocked(self) -> None:
        """Any address in the 169.254.0.0/16 link-local range is blocked."""
        with pytest.raises(ValueError, match="blocked"):
            _validate_provider_url("https://169.254.0.1")  # NOSONAR

    def test_metadata_google_internal_blocked(self) -> None:
        """GCP metadata hostname is blocked."""
        with pytest.raises(ValueError, match="blocked"):
            _validate_provider_url(
                "https://metadata.google.internal/computeMetadata/v1/"
            )

    def test_metadata_internal_blocked(self) -> None:
        """Generic metadata.internal hostname is blocked."""
        with pytest.raises(ValueError, match="blocked"):
            _validate_provider_url("https://metadata.internal/")

    def test_file_scheme_rejected(self) -> None:
        """Non-HTTPS file:// scheme raises ValueError."""
        with pytest.raises(ValueError, match="https"):
            _validate_provider_url("file:///etc/passwd")

    def test_ftp_scheme_rejected(self) -> None:
        """Non-HTTPS ftp:// scheme raises ValueError."""
        with pytest.raises(ValueError, match="https"):
            _validate_provider_url("ftp://example.com/webhook")

    def test_shared_address_space_blocked(self) -> None:
        """RFC 6598 shared address space must be blocked."""
        with pytest.raises(ValueError, match="blocked"):
            _validate_provider_url("https://100.64.0.1")  # NOSONAR

    def test_ipv6_link_local_blocked(self) -> None:
        """IPv6 link-local addresses (fe80::/10) are blocked."""
        with pytest.raises(ValueError, match="blocked"):
            _validate_provider_url("https://[fe80::1]/webhook")  # NOSONAR

    def test_ipv6_loopback_blocked(self) -> None:
        """IPv6 loopback literal (::1) is blocked as a hostname."""
        with pytest.raises(ValueError, match="blocked"):
            _validate_provider_url("https://[::1]/webhook")  # NOSONAR


# ---------------------------------------------------------------------------
# WebhookProvider
# ---------------------------------------------------------------------------


class TestWebhookProvider:
    """Tests for WebhookProvider HTTP POST alert delivery."""

    def test_send_alert_posts_json(self) -> None:
        """send_alert POSTs a JSON payload with failure_count, last_error, and source."""
        provider = WebhookProvider(url="https://example.com/hook")
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        with patch.object(
            provider._session, "post", return_value=mock_resp
        ) as mock_post:
            provider.send_alert(3, "poll failed", _ts())
            mock_post.assert_called_once()
            payload = mock_post.call_args.kwargs["json"]
            assert payload["failure_count"] == 3
            assert payload["last_error"] == "poll failed"
            assert payload["source"] == "Argus"

    def test_send_event_alert_posts_event_json(self) -> None:
        """send_event_alert POSTs event_type, device_id, and severity in the payload."""
        provider = WebhookProvider(url="https://example.com/hook")
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        with patch.object(
            provider._session, "post", return_value=mock_resp
        ) as mock_post:
            provider.send_event_alert(
                "on_battery", "dev-1", "UPS on battery", "high", _ts()
            )
            payload = mock_post.call_args.kwargs["json"]
            assert payload["event_type"] == "on_battery"
            assert payload["device_id"] == "dev-1"
            assert payload["severity"] == "high"

    def test_raises_on_http_error(self) -> None:
        """HTTP error from the endpoint is propagated to the caller."""
        provider = WebhookProvider(url="https://example.com/hook")
        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = requests.HTTPError("500")
        with patch.object(provider._session, "post", return_value=mock_resp):
            with pytest.raises(requests.HTTPError):
                provider.send_alert(1, "err", _ts())

    def test_constructor_rejects_metadata_ip(self) -> None:
        """Constructor rejects SSRF-dangerous metadata endpoint URLs."""
        with pytest.raises(ValueError, match="blocked"):
            WebhookProvider(url="https://169.254.169.254/hook")  # NOSONAR


# ---------------------------------------------------------------------------
# GotifyProvider
# ---------------------------------------------------------------------------


class TestGotifyProvider:
    """Tests for GotifyProvider message delivery and priority mapping."""

    def test_send_alert_uses_correct_endpoint(self) -> None:
        """send_alert POSTs to <base_url>/message."""
        provider = GotifyProvider(url="https://gotify.example.com", token="tok")
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        with patch.object(
            provider._session, "post", return_value=mock_resp
        ) as mock_post:
            provider.send_alert(2, "error", _ts())
            url_called = mock_post.call_args.args[0]
            assert url_called == "https://gotify.example.com/message"

    def test_send_alert_includes_token_header(self) -> None:
        """send_alert includes the Gotify token in the X-Gotify-Key header."""
        provider = GotifyProvider(url="https://gotify.example.com", token="my-token")
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        with patch.object(
            provider._session, "post", return_value=mock_resp
        ) as mock_post:
            provider.send_alert(1, "e", _ts())
            headers = mock_post.call_args.kwargs["headers"]
            assert headers["X-Gotify-Key"] == "my-token"

    def test_send_event_alert_critical_uses_priority_10(self) -> None:
        """Critical severity maps to Gotify priority 10."""
        provider = GotifyProvider(url="https://gotify.example.com", token="tok")
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        with patch.object(
            provider._session, "post", return_value=mock_resp
        ) as mock_post:
            provider.send_event_alert(
                "battery_low", "dev-1", "Battery critical", "critical", _ts()
            )
            payload = mock_post.call_args.kwargs["json"]
            assert payload["priority"] == 10

    def test_send_event_alert_low_uses_priority_3(self) -> None:
        """Low severity maps to Gotify priority 3."""
        provider = GotifyProvider(url="https://gotify.example.com", token="tok")
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        with patch.object(
            provider._session, "post", return_value=mock_resp
        ) as mock_post:
            provider.send_event_alert(
                "power_restored", "dev-1", "Power restored", "low", _ts()
            )
            payload = mock_post.call_args.kwargs["json"]
            assert payload["priority"] == 3

    def test_send_event_alert_high_uses_priority_8(self) -> None:
        """High severity maps to Gotify priority 8."""
        provider = GotifyProvider(url="https://gotify.example.com", token="tok")
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        with patch.object(
            provider._session, "post", return_value=mock_resp
        ) as mock_post:
            provider.send_event_alert(
                "on_battery", "dev-1", "On battery", "high", _ts()
            )
            payload = mock_post.call_args.kwargs["json"]
            assert payload["priority"] == 8

    def test_priority_override_used_in_send_event_alert(self) -> None:
        """Configured priority overrides severity-based Gotify priority."""
        provider = GotifyProvider(url="https://gotify.example.com", token="tok", priority=2)
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        with patch.object(
            provider._session, "post", return_value=mock_resp
        ) as mock_post:
            provider.send_event_alert(
                "battery_low", "dev-1", "Battery low", "critical", _ts()
            )
            payload = mock_post.call_args.kwargs["json"]
            assert payload["priority"] == 2

    def test_priority_override_used_in_send_alert(self) -> None:
        """Configured priority overrides the default 8 in send_alert."""
        provider = GotifyProvider(url="https://gotify.example.com", token="tok", priority=5)
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        with patch.object(
            provider._session, "post", return_value=mock_resp
        ) as mock_post:
            provider.send_alert(3, "timeout", _ts())
            payload = mock_post.call_args.kwargs["json"]
            assert payload["priority"] == 5


# ---------------------------------------------------------------------------
# NtfyProvider
# ---------------------------------------------------------------------------


class TestNtfyProvider:
    """Tests for NtfyProvider message delivery and priority/tag mapping."""

    def test_send_alert_posts_to_topic(self) -> None:
        """send_alert POSTs to <base_url>/<topic>."""
        provider = NtfyProvider(url="https://ntfy.sh", topic="argus-alerts")
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        with patch.object(
            provider._session, "post", return_value=mock_resp
        ) as mock_post:
            provider.send_alert(1, "err", _ts())
            url_called = mock_post.call_args.args[0]
            assert url_called == "https://ntfy.sh/argus-alerts"

    def test_send_event_alert_critical_uses_urgent_priority(self) -> None:
        """Critical severity maps to ntfy priority 'urgent'."""
        provider = NtfyProvider(url="https://ntfy.sh", topic="argus")
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        with patch.object(
            provider._session, "post", return_value=mock_resp
        ) as mock_post:
            provider.send_event_alert(
                "battery_low", "dev-1", "Battery low", "critical", _ts()
            )
            headers = mock_post.call_args.kwargs["headers"]
            assert headers["Priority"] == "urgent"

    def test_send_event_alert_low_uses_low_priority(self) -> None:
        """Low severity maps to ntfy priority 'low'."""
        provider = NtfyProvider(url="https://ntfy.sh", topic="argus")
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        with patch.object(
            provider._session, "post", return_value=mock_resp
        ) as mock_post:
            provider.send_event_alert(
                "power_restored", "dev-1", "Restored", "low", _ts()
            )
            headers = mock_post.call_args.kwargs["headers"]
            assert headers["Priority"] == "low"

    def test_send_event_alert_includes_event_type_as_tag(self) -> None:
        """event_type is forwarded as the ntfy Tags header."""
        provider = NtfyProvider(url="https://ntfy.sh", topic="argus")
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        with patch.object(
            provider._session, "post", return_value=mock_resp
        ) as mock_post:
            provider.send_event_alert(
                "on_battery", "dev-1", "On battery", "high", _ts()
            )
            headers = mock_post.call_args.kwargs["headers"]
            assert headers["Tags"] == "on_battery"

    def test_token_adds_authorization_header(self) -> None:
        """When token is set, Authorization: Bearer <token> is sent."""
        provider = NtfyProvider(
            url="https://ntfy.example.com", topic="argus", token="mytoken"
        )
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        with patch.object(
            provider._session, "post", return_value=mock_resp
        ) as mock_post:
            provider.send_alert(1, "err", _ts())
            headers = mock_post.call_args.kwargs["headers"]
            assert headers.get("Authorization") == "Bearer mytoken"

    def test_no_token_omits_authorization_header(self) -> None:
        """When no token is set, Authorization header is absent."""
        provider = NtfyProvider(url="https://ntfy.sh", topic="argus")
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        with patch.object(
            provider._session, "post", return_value=mock_resp
        ) as mock_post:
            provider.send_alert(1, "err", _ts())
            headers = mock_post.call_args.kwargs["headers"]
            assert "Authorization" not in headers

    def test_priority_override_used_instead_of_severity_mapping(self) -> None:
        """Configured priority overrides severity-based ntfy priority."""
        provider = NtfyProvider(
            url="https://ntfy.sh", topic="argus", priority="min"
        )
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        with patch.object(
            provider._session, "post", return_value=mock_resp
        ) as mock_post:
            provider.send_event_alert(
                "battery_low", "dev-1", "Battery low", "critical", _ts()
            )
            headers = mock_post.call_args.kwargs["headers"]
            assert headers["Priority"] == "min"

    def test_tags_override_replaces_event_type_tag(self) -> None:
        """Configured tags replace the default event_type tag."""
        provider = NtfyProvider(
            url="https://ntfy.sh", topic="argus", tags="warning,rotating_light"
        )
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        with patch.object(
            provider._session, "post", return_value=mock_resp
        ) as mock_post:
            provider.send_event_alert(
                "on_battery", "dev-1", "On battery", "high", _ts()
            )
            headers = mock_post.call_args.kwargs["headers"]
            assert headers["Tags"] == "warning,rotating_light"

    def test_tags_override_used_in_send_alert(self) -> None:
        """Configured tags replace the default 'warning' tag in send_alert."""
        provider = NtfyProvider(
            url="https://ntfy.sh", topic="argus", tags="ups,critical"
        )
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        with patch.object(
            provider._session, "post", return_value=mock_resp
        ) as mock_post:
            provider.send_alert(3, "timeout", _ts())
            headers = mock_post.call_args.kwargs["headers"]
            assert headers["Tags"] == "ups,critical"


# ---------------------------------------------------------------------------
# AppriseProvider
# ---------------------------------------------------------------------------


class TestAppriseProvider:
    """Tests for AppriseProvider JSON alert delivery."""

    def test_send_alert_posts_json(self) -> None:
        """send_alert POSTs a JSON payload with title and body keys."""
        provider = AppriseProvider(url="https://apprise.example.com/notify")
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        with patch.object(
            provider._session, "post", return_value=mock_resp
        ) as mock_post:
            provider.send_alert(2, "err", _ts())
            payload = mock_post.call_args.kwargs["json"]
            assert "title" in payload
            assert "body" in payload

    def test_send_event_alert_includes_severity_in_title(self) -> None:
        """send_event_alert includes the uppercased severity in the title."""
        provider = AppriseProvider(url="https://apprise.example.com/notify")
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        with patch.object(
            provider._session, "post", return_value=mock_resp
        ) as mock_post:
            provider.send_event_alert(
                "on_battery", "dev-1", "On battery", "high", _ts()
            )
            payload = mock_post.call_args.kwargs["json"]
            assert "HIGH" in payload["title"]

    def test_send_event_alert_body_contains_message(self) -> None:
        """send_event_alert includes the message string in the body."""
        provider = AppriseProvider(url="https://apprise.example.com/notify")
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        with patch.object(
            provider._session, "post", return_value=mock_resp
        ) as mock_post:
            provider.send_event_alert(
                "battery_low", "dev-1", "Battery critically low", "critical", _ts()
            )
            payload = mock_post.call_args.kwargs["json"]
            assert "Battery critically low" in payload["body"]


# ---------------------------------------------------------------------------
# Per-provider minimum severity filter
# ---------------------------------------------------------------------------


class TestMeetsMinSeverity:
    """Tests for AlertProvider.meets_min_severity severity filtering."""

    def test_default_min_severity_is_low_accepts_all(self) -> None:
        """Default min_severity='low' accepts every severity level."""
        provider = WebhookProvider(url="https://example.com/hook")
        for sev in ("low", "medium", "high", "critical"):
            assert provider.meets_min_severity(sev)

    def test_min_severity_critical_only_accepts_critical(self) -> None:
        """min_severity='critical' rejects low, medium, and high."""
        provider = WebhookProvider(
            url="https://example.com/hook", min_severity="critical"
        )
        assert not provider.meets_min_severity("low")
        assert not provider.meets_min_severity("medium")
        assert not provider.meets_min_severity("high")
        assert provider.meets_min_severity("critical")

    def test_min_severity_high_accepts_high_and_critical(self) -> None:
        """min_severity='high' accepts high and critical but rejects low and medium."""
        provider = WebhookProvider(url="https://example.com/hook", min_severity="high")
        assert not provider.meets_min_severity("low")
        assert not provider.meets_min_severity("medium")
        assert provider.meets_min_severity("high")
        assert provider.meets_min_severity("critical")

    def test_min_severity_medium_accepts_medium_and_above(self) -> None:
        """min_severity='medium' accepts medium, high, and critical but rejects low."""
        provider = WebhookProvider(
            url="https://example.com/hook", min_severity="medium"
        )
        assert not provider.meets_min_severity("low")
        assert provider.meets_min_severity("medium")
        assert provider.meets_min_severity("high")
        assert provider.meets_min_severity("critical")

    def test_min_severity_case_insensitive(self) -> None:
        """Severity comparison is case-insensitive."""
        provider = WebhookProvider(url="https://example.com/hook", min_severity="HIGH")
        assert provider.meets_min_severity("CRITICAL")
        assert not provider.meets_min_severity("LOW")

    def test_unknown_severity_treated_as_lowest(self) -> None:
        """Unknown severity string is treated as order 0 and passes a low filter."""
        provider = WebhookProvider(url="https://example.com/hook", min_severity="low")
        assert provider.meets_min_severity("unknown")  # 0 >= 0 → True

    def test_all_providers_accept_min_severity_kwarg(self) -> None:
        """All four provider classes accept min_severity as a constructor argument."""
        GotifyProvider(
            url="https://gotify.example.com", token="tok", min_severity="high"
        )
        NtfyProvider(url="https://ntfy.sh", topic="argus", min_severity="medium")
        AppriseProvider(
            url="https://apprise.example.com/notify", min_severity="critical"
        )
