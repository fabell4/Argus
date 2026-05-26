"""GET/PUT /api/config — runtime scheduler configuration."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, field_validator

from src import runtime_config
from src.api.auth import require_api_key
from src.constants import ExporterType

router = APIRouter(tags=["config"])

_VALID_EXPORTERS = frozenset(ExporterType)


class RuntimeConfigSchema(BaseModel):
    """Serialised runtime configuration record."""

    poll_interval_minutes: int
    enabled_exporters: list[str]
    scanning_disabled: bool
    scheduler_paused: bool
    # NUT connection
    nut_host: str = Field(
        default="localhost",
        description="NUT daemon hostname.",
    )
    nut_port: int = Field(
        default=3493,
        description="NUT daemon TCP port.",
    )
    nut_username: str = Field(
        default="",
        description="Optional NUT username.",
    )
    nut_password: str = Field(
        default="",
        description=(
            "Optional NUT password. Send an empty string to keep the existing "
            "stored password."
        ),
    )
    nut_ups_name: str = Field(
        default="ups",
        description=(
            "UPS name, or a comma-separated list of UPS names when "
            "auto-discover is disabled."
        ),
    )
    nut_auto_discover: bool = Field(
        default=True,
        description=(
            "When true, poll all devices returned by LIST UPS instead of nut_ups_name."
        ),
    )
    # Event thresholds
    device_offline_missed_polls: int = 3
    shutdown_battery_floor_pct: float = 5.0
    threshold_load_percent: float = 90.0
    threshold_temp_celsius: float = 50.0

    @field_validator("poll_interval_minutes")
    @staticmethod
    def _validate_interval(v: int) -> int:
        if v < 1 or v > 10080:
            raise ValueError("poll_interval_minutes must be between 1 and 10080.")
        return v

    @field_validator("enabled_exporters")
    @staticmethod
    def _validate_exporters(v: list[str]) -> list[str]:
        invalid = set(v) - _VALID_EXPORTERS
        if invalid:
            raise ValueError(f"Unknown exporters: {invalid}. Valid: {_VALID_EXPORTERS}")
        return v

    @field_validator("nut_port")
    @staticmethod
    def _validate_nut_port(v: int) -> int:
        if v < 1 or v > 65535:
            raise ValueError("nut_port must be between 1 and 65535.")
        return v

    @field_validator("device_offline_missed_polls")
    @staticmethod
    def _validate_offline_polls(v: int) -> int:
        if v < 1:
            raise ValueError("device_offline_missed_polls must be at least 1.")
        return v

    @field_validator("shutdown_battery_floor_pct", "threshold_load_percent")
    @staticmethod
    def _validate_pct(v: float) -> float:
        if v < 0 or v > 100:
            raise ValueError("Percentage must be between 0 and 100.")
        return v

    @field_validator("threshold_temp_celsius")
    @staticmethod
    def _validate_temp(v: float) -> float:
        if v < 0:
            raise ValueError("threshold_temp_celsius must be >= 0.")
        return v


@router.get(
    "/config",
    dependencies=[Depends(require_api_key)],
)
def get_config() -> RuntimeConfigSchema:
    """Return the current runtime configuration."""
    data = runtime_config.load()
    nut = runtime_config.get_nut_config()
    thr = runtime_config.get_threshold_config()
    return RuntimeConfigSchema(
        poll_interval_minutes=data.get("poll_interval_minutes", 5),
        enabled_exporters=data.get("enabled_exporters", ["sqlite"]),
        scanning_disabled=data.get("scanning_disabled", False),
        scheduler_paused=data.get("scheduler_paused", False),
        nut_host=nut["host"],
        nut_port=nut["port"],
        nut_username=nut["username"],
        nut_password="",  # never expose stored password  # nosec B105
        nut_ups_name=nut["ups_name"],
        nut_auto_discover=nut["auto_discover"],
        device_offline_missed_polls=thr["device_offline_missed_polls"],
        shutdown_battery_floor_pct=thr["shutdown_battery_floor_pct"],
        threshold_load_percent=thr["threshold_load_percent"],
        threshold_temp_celsius=thr["threshold_temp_celsius"],
    )


@router.put(
    "/config",
    dependencies=[Depends(require_api_key)],
)
def update_config(body: RuntimeConfigSchema) -> RuntimeConfigSchema:
    """Replace the runtime configuration with the provided values."""
    try:
        runtime_config.set_interval_minutes(body.poll_interval_minutes)
        runtime_config.set_enabled_exporters(body.enabled_exporters)
        data = runtime_config.load()
        data["scanning_disabled"] = body.scanning_disabled
        data["scheduler_paused"] = body.scheduler_paused
        data["nut_host"] = body.nut_host
        data["nut_port"] = body.nut_port
        data["nut_username"] = body.nut_username
        # Preserve existing password when client sends empty string
        if body.nut_password:
            data["nut_password"] = body.nut_password
        data["nut_ups_name"] = body.nut_ups_name
        data["nut_auto_discover"] = body.nut_auto_discover
        data["device_offline_missed_polls"] = body.device_offline_missed_polls
        data["shutdown_battery_floor_pct"] = body.shutdown_battery_floor_pct
        data["threshold_load_percent"] = body.threshold_load_percent
        data["threshold_temp_celsius"] = body.threshold_temp_celsius
        runtime_config.save(data)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc
    # Return with masked password
    return RuntimeConfigSchema(**{**body.model_dump(), "nut_password": ""})  # nosec B105
