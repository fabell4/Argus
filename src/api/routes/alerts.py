"""GET/PUT /api/alerts — alert provider configuration and test dispatch."""

from __future__ import annotations

from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import AfterValidator, BaseModel, Field

from src import runtime_config, shared_state
from src.api.auth import require_api_key
from src.constants import AlertSeverity

router = APIRouter(tags=["alerts"])


def _require_https(v: str) -> str:
    if not v.startswith("https://"):
        raise ValueError("URL must use https:// scheme (http is not permitted)")
    return v


_HttpsUrl = Annotated[str, AfterValidator(_require_https)]


class WebhookProviderConfig(BaseModel):
    """Alert provider config for generic webhook targets."""

    type: Literal["webhook"] = "webhook"
    enabled: bool = True
    url: _HttpsUrl
    min_severity: AlertSeverity = AlertSeverity.LOW


class GotifyProviderConfig(BaseModel):
    """Alert provider config for Gotify push notifications."""

    type: Literal["gotify"] = "gotify"
    enabled: bool = True
    url: _HttpsUrl
    token: str
    priority: int = 0
    min_severity: AlertSeverity = AlertSeverity.LOW


class NtfyProviderConfig(BaseModel):
    """Alert provider config for ntfy push notifications."""

    type: Literal["ntfy"] = "ntfy"
    enabled: bool = True
    url: _HttpsUrl
    topic: str
    token: str = ""
    priority: str = ""
    tags: str = ""
    min_severity: AlertSeverity = AlertSeverity.LOW


class AppriseProviderConfig(BaseModel):
    """Alert provider config for Apprise multi-service notifications."""

    type: Literal["apprise"] = "apprise"
    enabled: bool = True
    url: _HttpsUrl
    min_severity: AlertSeverity = AlertSeverity.LOW


AlertProviderConfig = Annotated[
    WebhookProviderConfig
    | GotifyProviderConfig
    | NtfyProviderConfig
    | AppriseProviderConfig,
    Field(discriminator="type"),
]


class AlertConfigSchema(BaseModel):
    """Request/response schema for alert configuration."""

    providers: list[AlertProviderConfig] = []
    failure_threshold: int = Field(default=3, ge=1, le=100)
    cooldown_seconds: int = Field(default=3600, ge=60, le=86400)
    alert_on_battery: bool = True
    alert_on_battery_low: bool = True
    alert_on_device_offline: bool = True
    alert_recovery_notifications: bool = True
    recovery_cooldown_seconds: int = Field(default=300, ge=60, le=86400)


@router.get("/alerts")
def get_alerts() -> AlertConfigSchema:
    """Return the current alert configuration."""
    data = runtime_config.load()
    alert_cfg: dict[str, Any] = data.get("alert_config", {})
    try:
        return AlertConfigSchema(**alert_cfg) if alert_cfg else AlertConfigSchema()
    except (TypeError, ValueError):
        return AlertConfigSchema()


@router.put("/alerts", dependencies=[Depends(require_api_key)])
def update_alerts(body: AlertConfigSchema) -> AlertConfigSchema:
    """Persist a new alert configuration and return it."""
    data = runtime_config.load()
    data["alert_config"] = body.model_dump()
    runtime_config.save(data)
    return body


@router.post("/alerts/test", dependencies=[Depends(require_api_key)])
def test_alert() -> dict[str, str]:
    """Dispatch a test alert through all enabled providers."""
    alert_mgr = shared_state.get_alert_manager()
    if alert_mgr is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Alert manager not available (scheduler not running).",
        )
    try:
        alert_mgr.send_test_alert()
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=str(exc),
        ) from exc
    return {"status": "ok", "message": "Test alert dispatched."}
