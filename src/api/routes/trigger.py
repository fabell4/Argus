"""POST /api/trigger — manually trigger an immediate poll cycle."""

from __future__ import annotations

import threading

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from src import runtime_config
from src.api.auth import require_api_key

router = APIRouter(tags=["trigger"])

_poll_lock = threading.Lock()


class TriggerResponse(BaseModel):
    """Response model for trigger and poll-status endpoints."""

    status: str
    message: str


@router.post(
    "/trigger",
    dependencies=[Depends(require_api_key)],
)
def trigger_poll() -> TriggerResponse:
    """Signal the scheduler to run an immediate poll."""
    if runtime_config.is_running():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A poll is already in progress.",
        )
    runtime_config.trigger_poll()
    return TriggerResponse(status="accepted", message="Poll trigger queued.")


@router.get("/trigger/status")
def poll_status() -> TriggerResponse:
    """Return the current poll status."""
    if runtime_config.is_running():
        return TriggerResponse(status="running", message="Poll in progress.")
    return TriggerResponse(status="idle", message="No active poll.")
