"""GET/PUT/POST/DELETE /api/devices — device registry."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from src.api.auth import require_api_key
from src.services import device_registry

router = APIRouter(tags=["devices"])

_DEVICE_NOT_FOUND = "Device not found."


class DeviceSchema(BaseModel):
    """Serialised device registry record."""

    id: str
    name: str
    type: str
    poller: str
    host: str
    port: int
    enabled: bool = True
    connection_config: dict[str, Any] = {}
    model: str | None = None
    firmware: str | None = None
    serial: str | None = None
    manufacturer: str | None = None
    last_seen: str | None = None


@router.get("/devices")
def list_devices() -> list[DeviceSchema]:
    """Return all registered devices."""
    return [DeviceSchema(**d) for d in device_registry.load_devices()]


@router.get("/devices/{device_id}")
def get_device(device_id: str) -> DeviceSchema:
    """Return a single device by ID."""
    d = device_registry.get_device(device_id)
    if d is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=_DEVICE_NOT_FOUND
        )
    return DeviceSchema(**d)


@router.post(
    "/devices",
    dependencies=[Depends(require_api_key)],
    status_code=status.HTTP_201_CREATED,
)
def add_device(device: DeviceSchema) -> DeviceSchema:
    """Register a new device; returns 409 if the ID already exists."""
    if device_registry.get_device(device.id) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Device '{device.id}' already exists. Use PUT to update.",
        )
    device_registry.upsert_device(device.model_dump())
    return device


@router.put("/devices", dependencies=[Depends(require_api_key)])
def replace_devices(devices: list[DeviceSchema]) -> list[DeviceSchema]:
    """Replace the entire device list."""
    device_registry.save_devices([d.model_dump() for d in devices])
    return devices


@router.put("/devices/{device_id}", dependencies=[Depends(require_api_key)])
def update_device(device_id: str, device: DeviceSchema) -> DeviceSchema:
    """Update an existing device by ID."""
    if device_registry.get_device(device_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=_DEVICE_NOT_FOUND
        )
    if device.id != device_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Device ID in body must match path parameter.",
        )
    device_registry.upsert_device(device.model_dump())
    return device


@router.delete(
    "/devices/{device_id}",
    dependencies=[Depends(require_api_key)],
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_device(device_id: str) -> None:
    """Delete a device by ID; returns 404 if not found."""
    if not device_registry.remove_device(device_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=_DEVICE_NOT_FOUND
        )
