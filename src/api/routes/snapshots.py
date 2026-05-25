"""GET /api/snapshots — paginated power snapshot history."""
from __future__ import annotations

import sqlite3
from contextlib import closing
from typing import Annotated, Any

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel

from src.api.db import _DB_UNAVAILABLE, get_conn

router = APIRouter(tags=["snapshots"])

_PAGE_SIZE_MAX = 200


class SnapshotSchema(BaseModel):
    """Serialised power snapshot record."""

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
    """Paginated snapshots response."""

    page: int
    page_size: int
    total: int
    items: list[SnapshotSchema]


@router.get("/snapshots")
def list_snapshots(
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=_PAGE_SIZE_MAX)] = 50,
    device_id: Annotated[str | None, Query()] = None,
) -> SnapshotsPage:
    """Return a paginated list of power snapshots, optionally filtered by device_id."""
    try:
        with closing(get_conn()) as conn:
            offset = (page - 1) * page_size

            where = "WHERE device_id = ?" if device_id else ""
            params_count: list[Any] = [device_id] if device_id else []
            params_rows: list[Any] = (
                [device_id, page_size, offset] if device_id else [page_size, offset]
            )

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
            detail=_DB_UNAVAILABLE,
        ) from exc


@router.get("/snapshots/latest")
def latest_snapshot(
    device_id: Annotated[str | None, Query()] = None,
) -> SnapshotSchema | None:
    """Return the most recent snapshot, optionally filtered by device_id."""
    try:
        with closing(get_conn()) as conn:
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
            detail=_DB_UNAVAILABLE,
        ) from exc
