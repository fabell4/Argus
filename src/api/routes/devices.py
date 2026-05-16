"""GET/PUT /api/devices — device registry."""
from __future__ import annotations

import json
import os
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from src.api.auth import require_api_key

router = APIRouter(tags=["devices"])

_DEVICES_FILE = os.path.join("data", "devices.json")


class DeviceSchema(BaseModel):
    id: str
    name: str
    type: str
    poller: str
    host: str
    port: int
    enabled: bool = True
    connection_config: dict[str, Any] = {}


def _load_devices() -> list[dict[str, Any]]:
    if not os.path.exists(_DEVICES_FILE):
        return []
    with open(_DEVICES_FILE, encoding="utf-8") as fh:
        devices: list[dict[str, Any]] = json.load(fh)
        return devices


def _save_devices(devices: list[dict[str, Any]]) -> None:
    os.makedirs(os.path.dirname(_DEVICES_FILE), exist_ok=True)
    with open(_DEVICES_FILE, "w", encoding="utf-8") as fh:
        json.dump(devices, fh, indent=2)


@router.get("/devices")
def list_devices() -> list[DeviceSchema]:
    return [DeviceSchema(**d) for d in _load_devices()]


@router.get("/devices/{device_id}")
def get_device(device_id: str) -> DeviceSchema:
    for d in _load_devices():
        if d["id"] == device_id:
            return DeviceSchema(**d)
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found.")


@router.put("/devices", dependencies=[Depends(require_api_key)])
def replace_devices(devices: list[DeviceSchema]) -> list[DeviceSchema]:
    _save_devices([d.model_dump() for d in devices])
    return devices
