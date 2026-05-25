"""GET/PUT /api/config — runtime scheduler configuration."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, field_validator

from src import runtime_config
from src.api.auth import require_api_key
from src.constants import ExporterType

router = APIRouter(tags=["config"])

_VALID_EXPORTERS = frozenset(ExporterType)


class RuntimeConfigSchema(BaseModel):
    poll_interval_minutes: int
    enabled_exporters: list[str]
    scanning_disabled: bool
    scheduler_paused: bool

    @field_validator("poll_interval_minutes")
    @classmethod
    def _validate_interval(cls, v: int) -> int:
        if v < 1 or v > 10080:
            raise ValueError("poll_interval_minutes must be between 1 and 10080.")
        return v

    @field_validator("enabled_exporters")
    @classmethod
    def _validate_exporters(cls, v: list[str]) -> list[str]:
        invalid = set(v) - _VALID_EXPORTERS
        if invalid:
            raise ValueError(f"Unknown exporters: {invalid}. Valid: {_VALID_EXPORTERS}")
        return v


@router.get("/config")
def get_config() -> RuntimeConfigSchema:
    data = runtime_config.load()
    return RuntimeConfigSchema(
        poll_interval_minutes=data.get("poll_interval_minutes", 5),
        enabled_exporters=data.get("enabled_exporters", ["sqlite"]),
        scanning_disabled=data.get("scanning_disabled", False),
        scheduler_paused=data.get("scheduler_paused", False),
    )


@router.put(
    "/config",
    dependencies=[Depends(require_api_key)],
)
def update_config(body: RuntimeConfigSchema) -> RuntimeConfigSchema:
    try:
        runtime_config.set_interval_minutes(body.poll_interval_minutes)
        runtime_config.set_enabled_exporters(body.enabled_exporters)
        data = runtime_config.load()
        data["scanning_disabled"] = body.scanning_disabled
        data["scheduler_paused"] = body.scheduler_paused
        runtime_config.save(data)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    return body
