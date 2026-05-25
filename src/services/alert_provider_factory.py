"""Factory functions for registering alert providers with the AlertManager."""

from __future__ import annotations

import logging
from typing import Any

from src import config
from src.constants import AlertProviderType
from src.services.alert_manager import AlertManager
from src.services.alert_providers import (
    AppriseProvider,
    GotifyProvider,
    NtfyProvider,
    WebhookProvider,
)

_LOG = logging.getLogger(__name__)


def _get_config_value(runtime_key: str, env_value: str) -> str:
    """Return runtime alert config value with fall-through to env var."""
    from src import runtime_config

    alert_cfg: dict[str, Any] = runtime_config.get_alert_config()
    return alert_cfg.get(runtime_key) or env_value


def _get_provider_min_severity(provider_type: str) -> str:
    """Return the min_severity configured for a provider type, defaulting to 'low'."""
    from src import runtime_config

    alert_cfg: dict[str, Any] = runtime_config.get_alert_config()
    for p in alert_cfg.get("providers", []):
        if isinstance(p, dict) and p.get("type") == provider_type:
            return str(p.get("min_severity", "low"))
    return "low"


def register_webhook_provider(manager: AlertManager) -> None:
    """Register a WebhookProvider if WEBHOOK_URL is configured."""
    url = _get_config_value("webhook_url", config.WEBHOOK_URL)
    if url:
        min_sev = _get_provider_min_severity(AlertProviderType.WEBHOOK)
        manager.add_provider(WebhookProvider(url=url, min_severity=min_sev))
        _LOG.info("Registered WebhookProvider.")


def register_gotify_provider(manager: AlertManager) -> None:
    """Register a GotifyProvider if both GOTIFY_URL and GOTIFY_TOKEN are configured."""
    url = _get_config_value("gotify_url", config.GOTIFY_URL)
    token = _get_config_value("gotify_token", config.GOTIFY_TOKEN)
    if url and token:
        min_sev = _get_provider_min_severity(AlertProviderType.GOTIFY)
        manager.add_provider(GotifyProvider(url=url, token=token, min_severity=min_sev))
        _LOG.info("Registered GotifyProvider.")


def register_ntfy_provider(manager: AlertManager) -> None:
    """Register an NtfyProvider if both NTFY_URL and NTFY_TOPIC are configured."""
    url = _get_config_value("ntfy_url", config.NTFY_URL)
    topic = _get_config_value("ntfy_topic", config.NTFY_TOPIC)
    if url and topic:
        min_sev = _get_provider_min_severity(AlertProviderType.NTFY)
        manager.add_provider(NtfyProvider(url=url, topic=topic, min_severity=min_sev))
        _LOG.info("Registered NtfyProvider.")


def register_apprise_provider(manager: AlertManager) -> None:
    """Register an AppriseProvider if APPRISE_URL is configured."""
    url = _get_config_value("apprise_url", config.APPRISE_URL)
    if url:
        min_sev = _get_provider_min_severity(AlertProviderType.APPRISE)
        manager.add_provider(AppriseProvider(url=url, min_severity=min_sev))
        _LOG.info("Registered AppriseProvider.")


def register_all_providers(manager: AlertManager) -> None:
    """Register all configured alert providers with the given AlertManager."""
    register_webhook_provider(manager)
    register_gotify_provider(manager)
    register_ntfy_provider(manager)
    register_apprise_provider(manager)
