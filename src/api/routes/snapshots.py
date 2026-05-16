"""GET /api/snapshots — paginated power snapshot history."""
from __future__ import annotations

import sqlite3
from typing import Any

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel

from src import config

router = APIRouter(tags=["snapshots"])

_PAGE_SIZE_MAX = 200


class SnapshotSchema(BaseModel):
    id: int
    timestamp: str
    device_id: str
    device_type: str
    power_watts: float | None = None
    load_percent: float | None = None
    voltage: float | None = None
    battery_percent: float | None = None
    runtime_seconds: float | None = None
    ups_status: str | None = None
    temperature_c: float | None = None


class SnapshotsPage(BaseModel):
    page: int
    page_size: int
    total: int
    items: list[SnapshotSchema]


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(config.SQLITE_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


@router.get("/snapshots", response_model=SnapshotsPage)
def list_snapshots(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=_PAGE_SIZE_MAX),
    device_id: str | None = Query(default=None),
) -> SnapshotsPage:
    try:
        conn = _get_conn()
        offset = (page - 1) * page_size

        where = "WHERE device_id = ?" if device_id else ""
        params_count: list[Any] = [device_id] if device_id else []
        params_rows: list[Any] = [device_id, page_size, offset] if device_id else [page_size, offset]

        total_row = conn.execute(
            f"SELECT COUNT(*) FROM power_snapshots {where}", params_count
        ).fetchone()
        total = total_row[0] if total_row else 0

        rows = conn.execute(
            f"SELECT * FROM power_snapshots {where} "
            "ORDER BY timestamp DESC LIMIT ? OFFSET ?",
            params_rows,
        ).fetchall()

        items = [SnapshotSchema(**dict(row)) for row in rows]
        return SnapshotsPage(page=page, page_size=page_size, total=total, items=items)
    except sqlite3.OperationalError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database unavailable.",
        ) from exc


@router.get("/snapshots/latest", response_model=SnapshotSchema | None)
def latest_snapshot(device_id: str | None = Query(default=None)) -> SnapshotSchema | None:
    try:
        conn = _get_conn()
        where = "WHERE device_id = ?" if device_id else ""
        params: list[Any] = [device_id] if device_id else []
        row = conn.execute(
            f"SELECT * FROM power_snapshots {where} ORDER BY timestamp DESC LIMIT 1",
            params,
        ).fetchone()
        return SnapshotSchema(**dict(row)) if row else None
    except sqlite3.OperationalError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database unavailable.",
        ) from exc
