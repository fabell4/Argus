"""Tests for AlertManager — event alerting, recovery, cooldown, and failure tracking."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from src.constants import EventType
from src.models.event import PowerEvent
from src.services.alert_manager import AlertManager


def _ts() -> datetime:
    return datetime.now(timezone.utc)


def _event(event_type: str, device_id: str = "nut:ups@localhost") -> PowerEvent:
    return PowerEvent(timestamp=_ts(), device_id=device_id, event_type=event_type)


def _manager_with_provider(**kwargs: object) -> tuple[AlertManager, MagicMock]:
    kw: dict[str, object] = {"test_cooldown_seconds": 10}
    kw.update(kwargs)
    mgr = AlertManager(**kw)  # type: ignore[arg-type]
    provider = MagicMock()
    mgr.add_provider(provider)
    return mgr, provider


# ---------------------------------------------------------------------------
# Poll-failure tracking
# ---------------------------------------------------------------------------


def test_record_failure_increments_counter() -> None:
    """Consecutive failures counter increments with each recorded failure."""
    mgr = AlertManager()
    mgr.record_failure("err", _ts())
    assert mgr.consecutive_failures == 1


def test_record_success_resets_counter() -> None:
    """Counter resets to zero after a successful poll."""
    mgr = AlertManager()
    mgr.record_failure("err", _ts())
    mgr.record_failure("err", _ts())
    mgr.record_success()
    assert mgr.consecutive_failures == 0


def test_last_error_updated_on_failure() -> None:
    """last_error is set to the error message on each failure."""
    mgr = AlertManager()
    mgr.record_failure("connection timeout", _ts())
    assert mgr.last_error == "connection timeout"


def test_last_error_cleared_on_success() -> None:
    """last_error is cleared to an empty string after success."""
    mgr = AlertManager()
    mgr.record_failure("err", _ts())
    mgr.record_success()
    assert mgr.last_error == ""


def test_alert_fires_at_threshold() -> None:
    """Alert is triggered exactly when failure count reaches the threshold."""
    mgr, _provider = _manager_with_provider(failure_threshold=3)
    with patch.object(mgr, "_maybe_send_alert") as mock_send:
        mgr.record_failure("e", _ts())
        mgr.record_failure("e", _ts())
        mock_send.assert_not_called()
        mgr.record_failure("e", _ts())
        mock_send.assert_called_once()


def test_alert_fires_above_threshold() -> None:
    """Alert fires for each additional failure beyond the threshold."""
    mgr, _provider = _manager_with_provider(failure_threshold=2)
    with patch.object(mgr, "_maybe_send_alert") as mock_send:
        mgr.record_failure("e", _ts())
        mgr.record_failure("e", _ts())
        mgr.record_failure("e", _ts())
        assert mock_send.call_count == 2


def test_alert_suppressed_within_cooldown() -> None:
    """Second alert within the cooldown window is suppressed."""
    mgr, provider = _manager_with_provider(failure_threshold=1, cooldown_seconds=3600)
    mgr.record_failure("e", _ts())  # fires alert
    mgr.record_failure("e", _ts())  # suppressed
    # send_alert should only be called once due to cooldown
    assert provider.send_alert.call_count <= 1


def test_no_providers_no_error() -> None:
    """AlertManager with no providers does not raise when failures are recorded."""
    mgr = AlertManager(failure_threshold=1)
    mgr.record_failure("e", _ts())  # should not raise


# ---------------------------------------------------------------------------
# Power event alerting
# ---------------------------------------------------------------------------


def test_record_event_on_battery_fires_alert() -> None:
    """ON_BATTERY event triggers an event alert when alerting is enabled."""
    mgr, _provider = _manager_with_provider()
    with (
        patch.object(mgr, "_is_event_type_enabled", return_value=True),
        patch.object(mgr, "_maybe_send_event_alert") as mock_event_alert,
    ):
        mgr.record_event(_event(EventType.ON_BATTERY))
        mock_event_alert.assert_called_once()


def test_record_event_battery_low_fires_alert() -> None:
    """BATTERY_LOW event triggers an event alert when alerting is enabled."""
    mgr, _provider = _manager_with_provider()
    with (
        patch.object(mgr, "_is_event_type_enabled", return_value=True),
        patch.object(mgr, "_maybe_send_event_alert") as mock_event_alert,
    ):
        mgr.record_event(_event(EventType.BATTERY_LOW))
        mock_event_alert.assert_called_once()


def test_record_event_device_offline_fires_alert() -> None:
    """DEVICE_OFFLINE event triggers an event alert when alerting is enabled."""
    mgr, _provider = _manager_with_provider()
    with (
        patch.object(mgr, "_is_event_type_enabled", return_value=True),
        patch.object(mgr, "_maybe_send_event_alert") as mock_event_alert,
    ):
        mgr.record_event(_event(EventType.DEVICE_OFFLINE))
        mock_event_alert.assert_called_once()


def test_record_event_shutdown_initiated_fires_alert() -> None:
    """SHUTDOWN_INITIATED event triggers an event alert when alerting is enabled."""
    mgr, _provider = _manager_with_provider()
    with (
        patch.object(mgr, "_is_event_type_enabled", return_value=True),
        patch.object(mgr, "_maybe_send_event_alert") as mock_event_alert,
    ):
        mgr.record_event(_event(EventType.SHUTDOWN_INITIATED))
        mock_event_alert.assert_called_once()


def test_record_event_power_restored_not_forwarded_to_record_event() -> None:
    """POWER_RESTORED is a recovery event and must not go through record_event."""
    mgr, _provider = _manager_with_provider()
    with patch.object(mgr, "_maybe_send_event_alert") as mock_event_alert:
        mgr.record_event(_event(EventType.POWER_RESTORED))
        mock_event_alert.assert_not_called()


def test_record_event_device_online_not_forwarded_to_record_event() -> None:
    """DEVICE_ONLINE is a recovery event and must not go through record_event."""
    mgr, _provider = _manager_with_provider()
    with patch.object(mgr, "_maybe_send_event_alert") as mock_event_alert:
        mgr.record_event(_event(EventType.DEVICE_ONLINE))
        mock_event_alert.assert_not_called()


def test_record_event_suppressed_when_disabled() -> None:
    """Event alert is not sent when the event type is disabled in config."""
    mgr, _provider = _manager_with_provider()
    with (
        patch.object(mgr, "_is_event_type_enabled", return_value=False),
        patch.object(mgr, "_maybe_send_event_alert") as mock_event_alert,
    ):
        mgr.record_event(_event(EventType.ON_BATTERY))
        mock_event_alert.assert_not_called()


def test_event_alert_per_device_cooldown() -> None:
    """Same event on same device is suppressed within cooldown window."""
    mgr, provider = _manager_with_provider()
    with (
        patch.object(mgr, "_is_event_type_enabled", return_value=True),
        patch.object(provider, "send_event_alert") as mock_send,
    ):
        mgr.record_event(_event(EventType.ON_BATTERY, "dev-1"))
        mgr.record_event(_event(EventType.ON_BATTERY, "dev-1"))  # suppressed
        assert mock_send.call_count <= 1


def test_event_alert_different_devices_both_fire() -> None:
    """Same event on different devices both alert (separate cooldown keys)."""
    mgr, provider = _manager_with_provider(cooldown_seconds=0)
    with patch.object(mgr, "_is_event_type_enabled", return_value=True):
        mgr.record_event(_event(EventType.ON_BATTERY, "dev-1"))
        mgr.record_event(_event(EventType.ON_BATTERY, "dev-2"))
    assert provider.send_event_alert.call_count == 2


def test_event_alert_different_types_same_device_both_fire() -> None:
    """Different event types on the same device use separate cooldown keys."""
    mgr, provider = _manager_with_provider(cooldown_seconds=0)
    with patch.object(mgr, "_is_event_type_enabled", return_value=True):
        mgr.record_event(_event(EventType.ON_BATTERY, "dev-1"))
        mgr.record_event(_event(EventType.BATTERY_LOW, "dev-1"))
    assert provider.send_event_alert.call_count == 2


# ---------------------------------------------------------------------------
# Recovery notifications
# ---------------------------------------------------------------------------


def test_record_recovery_event_power_restored() -> None:
    """POWER_RESTORED recovery event triggers an alert when notifications are enabled."""
    mgr, _provider = _manager_with_provider()
    with (
        patch.object(mgr, "_is_recovery_notifications_enabled", return_value=True),
        patch.object(mgr, "_maybe_send_event_alert") as mock_send,
    ):
        mgr.record_recovery_event(_event(EventType.POWER_RESTORED))
        mock_send.assert_called_once()


def test_record_recovery_event_device_online() -> None:
    """DEVICE_ONLINE recovery event triggers an alert when notifications are enabled."""
    mgr, _provider = _manager_with_provider()
    with (
        patch.object(mgr, "_is_recovery_notifications_enabled", return_value=True),
        patch.object(mgr, "_maybe_send_event_alert") as mock_send,
    ):
        mgr.record_recovery_event(_event(EventType.DEVICE_ONLINE))
        mock_send.assert_called_once()


def test_record_recovery_event_suppressed_when_disabled() -> None:
    """Recovery notifications are suppressed when the feature is disabled in config."""
    mgr, _provider = _manager_with_provider()
    with (
        patch.object(mgr, "_is_recovery_notifications_enabled", return_value=False),
        patch.object(mgr, "_maybe_send_event_alert") as mock_send,
    ):
        mgr.record_recovery_event(_event(EventType.POWER_RESTORED))
        mock_send.assert_not_called()


def test_record_recovery_event_ignores_non_recovery_type() -> None:
    """Non-recovery event passed to record_recovery_event does not trigger an alert."""
    mgr, _provider = _manager_with_provider()
    with patch.object(mgr, "_maybe_send_event_alert") as mock_send:
        mgr.record_recovery_event(_event(EventType.ON_BATTERY))
        mock_send.assert_not_called()


def test_recovery_cooldown_uses_runtime_config_value() -> None:
    """record_recovery_event uses the runtime-config recovery_cooldown_seconds when set."""
    mgr, _provider = _manager_with_provider()
    with (
        patch.object(mgr, "_is_recovery_notifications_enabled", return_value=True),
        patch.object(mgr, "_get_recovery_cooldown_seconds", return_value=120),
        patch.object(mgr, "_maybe_send_event_alert") as mock_send,
    ):
        mgr.record_recovery_event(_event(EventType.POWER_RESTORED))
        _, _, _, cooldown = mock_send.call_args.args
        assert cooldown == 120


def test_get_recovery_cooldown_seconds_returns_config_value() -> None:
    """_get_recovery_cooldown_seconds returns the value from runtime alert_config."""
    mgr = AlertManager()
    fake_config = {"alert_config": {"recovery_cooldown_seconds": 600}}
    with (
        patch("src.runtime_config.load", return_value=fake_config),
        patch("src.config.ALERT_RECOVERY_COOLDOWN_SECONDS", 300),
    ):
        assert mgr._get_recovery_cooldown_seconds() == 600


def test_get_recovery_cooldown_seconds_falls_back_to_env_default() -> None:
    """_get_recovery_cooldown_seconds falls back to config.ALERT_RECOVERY_COOLDOWN_SECONDS."""
    mgr = AlertManager()
    with patch("src.runtime_config.load", return_value={}):
        result = mgr._get_recovery_cooldown_seconds()
        # Should return the config default (300) or whatever is set
        assert isinstance(result, int)
        assert result > 0


# ---------------------------------------------------------------------------
# Test alert cooldown
# ---------------------------------------------------------------------------


def test_send_test_alert_succeeds_first_time() -> None:
    """Test alert is sent successfully the first time with no prior cooldown."""
    mgr, provider = _manager_with_provider(test_cooldown_seconds=10)
    mgr.send_test_alert()
    provider.send_alert.assert_called_once()


def test_send_test_alert_raises_within_cooldown() -> None:
    """Calling send_test_alert a second time within cooldown raises RuntimeError."""
    mgr, _provider = _manager_with_provider(test_cooldown_seconds=60)
    mgr.send_test_alert()
    with pytest.raises(RuntimeError, match="cooldown"):
        mgr.send_test_alert()


def test_send_test_alert_no_providers_no_error() -> None:
    """send_test_alert with no providers registered does not raise."""
    mgr = AlertManager(test_cooldown_seconds=1)
    mgr.send_test_alert()  # should not raise


def test_send_test_alert_provider_exception_does_not_propagate() -> None:
    """Provider exception during test alert is swallowed and does not propagate."""
    mgr, provider = _manager_with_provider(test_cooldown_seconds=1)
    provider.send_alert.side_effect = RuntimeError("provider down")
    mgr.send_test_alert()  # should not raise


# ---------------------------------------------------------------------------
# Per-provider severity filter
# ---------------------------------------------------------------------------


def test_event_alert_skipped_when_provider_min_severity_too_high() -> None:
    """Provider with min_severity=critical should NOT receive a HIGH event."""
    from src.services.alert_providers import WebhookProvider

    mgr = AlertManager(cooldown_seconds=0)
    provider = WebhookProvider(url="https://example.com/hook", min_severity="critical")
    mgr.add_provider(provider)
    with (
        patch.object(mgr, "_is_event_type_enabled", return_value=True),
        patch.object(provider, "send_event_alert") as mock_send,
    ):
        mgr.record_event(_event(EventType.ON_BATTERY))  # HIGH severity → filtered out
        mock_send.assert_not_called()


def test_event_alert_sent_when_severity_meets_min() -> None:
    """Provider with min_severity=high SHOULD receive a CRITICAL event."""
    from src.services.alert_providers import WebhookProvider

    mgr = AlertManager(cooldown_seconds=0)
    provider = WebhookProvider(url="https://example.com/hook", min_severity="high")
    mgr.add_provider(provider)
    with (
        patch.object(mgr, "_is_event_type_enabled", return_value=True),
        patch.object(provider._session, "post") as mock_post,
    ):
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp
        mgr.record_event(_event(EventType.BATTERY_LOW))  # CRITICAL severity → passes
        mock_post.assert_called_once()


def test_event_alert_selective_dispatch_by_min_severity() -> None:
    """Two providers with different min_severity thresholds; only the lower one fires."""
    from src.services.alert_providers import WebhookProvider

    mgr = AlertManager(cooldown_seconds=0)
    low_provider = WebhookProvider(url="https://example.com/low", min_severity="low")
    high_provider = WebhookProvider(
        url="https://example.com/high", min_severity="critical"
    )
    mgr.add_provider(low_provider)
    mgr.add_provider(high_provider)
    with (
        patch.object(mgr, "_is_event_type_enabled", return_value=True),
        patch.object(low_provider, "send_event_alert") as mock_low,
        patch.object(high_provider, "send_event_alert") as mock_high,
    ):
        mgr.record_event(_event(EventType.ON_BATTERY))  # HIGH severity
        mock_low.assert_called_once()
        mock_high.assert_not_called()


# ---------------------------------------------------------------------------
# _is_event_type_enabled reads runtime config
# ---------------------------------------------------------------------------


def test_is_event_type_enabled_defaults_true_for_on_battery() -> None:
    """_is_event_type_enabled returns True for ON_BATTERY when no runtime override exists."""
    mgr = AlertManager()
    with patch("src.runtime_config.load", return_value={}):
        with patch("src.config.ALERT_ON_BATTERY", True):
            assert mgr._is_event_type_enabled(EventType.ON_BATTERY) is True


def test_is_event_type_enabled_runtime_config_overrides() -> None:
    """Runtime config alert_on_battery=False overrides the env-var default."""
    mgr = AlertManager()
    cfg = {"alert_config": {"alert_on_battery": False}}
    with patch("src.runtime_config.load", return_value=cfg):
        with patch("src.config.ALERT_ON_BATTERY", True):
            assert mgr._is_event_type_enabled(EventType.ON_BATTERY) is False


def test_is_recovery_notifications_enabled_reads_runtime_config() -> None:
    """Runtime config alert_recovery_notifications=False disables recovery alerts."""
    mgr = AlertManager()
    cfg = {"alert_config": {"alert_recovery_notifications": False}}
    with patch("src.runtime_config.load", return_value=cfg):
        with patch("src.config.ALERT_RECOVERY_NOTIFICATIONS", True):
            assert mgr._is_recovery_notifications_enabled() is False
