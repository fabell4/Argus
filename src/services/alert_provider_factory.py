"""Factory functions for registering alert providers with the AlertManager."""
from __future__ import annotations

import logging
from typing import Any

from src import config
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


def register_webhook_provider(manager: AlertManager) -> None:
    url = _get_config_value("webhook_url", config.WEBHOOK_URL)
    if url:
        manager.add_provider(WebhookProvider(url=url))
        _LOG.info("Registered WebhookProvider.")


def register_gotify_provider(manager: AlertManager) -> None:
    url = _get_config_value("gotify_url", config.GOTIFY_URL)
    token = _get_config_value("gotify_token", config.GOTIFY_TOKEN)
    if url and token:
        manager.add_provider(GotifyProvider(url=url, token=token))
        _LOG.info("Registered GotifyProvider.")


def register_ntfy_provider(manager: AlertManager) -> None:
    url = _get_config_value("ntfy_url", config.NTFY_URL)
    topic = _get_config_value("ntfy_topic", config.NTFY_TOPIC)
    if url and topic:
        manager.add_provider(NtfyProvider(url=url, topic=topic))
        _LOG.info("Registered NtfyProvider.")


def register_apprise_provider(manager: AlertManager) -> None:
    url = _get_config_value("apprise_url", config.APPRISE_URL)
    if url:
        manager.add_provider(AppriseProvider(url=url))
        _LOG.info("Registered AppriseProvider.")


def register_all_providers(manager: AlertManager) -> None:
    register_webhook_provider(manager)
    register_gotify_provider(manager)
    register_ntfy_provider(manager)
    register_apprise_provider(manager)
