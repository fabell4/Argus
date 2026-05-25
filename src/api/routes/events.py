"""GET /api/events — power event history."""
from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from typing import Annotated, Any

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel

from src.api.db import _DB_UNAVAILABLE, get_conn

router = APIRouter(tags=["events"])

_PAGE_SIZE_MAX = 200


class EventSchema(BaseModel):
    """Serialised power event record."""

    id: int
    timestamp: str
    device_id: str
    event_type: str
    metadata: dict[str, Any]


class EventsPage(BaseModel):
    """Paginated power events response."""

    page: int
    page_size: int
    total: int
    items: list[EventSchema]


@router.get("/events")
def list_events(
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=_PAGE_SIZE_MAX)] = 50,
    device_id: Annotated[str | None, Query()] = None,
    event_type: Annotated[str | None, Query()] = None,
) -> EventsPage:
    """Return a paginated list of power events, optionally filtered by device and type."""
    try:
        with closing(get_conn()) as conn:
            offset = (page - 1) * page_size

            conditions: list[str] = []
            params: list[Any] = []
            if device_id:
                conditions.append("device_id = ?")
                params.append(device_id)
            if event_type:
                conditions.append("event_type = ?")
                params.append(event_type)

            where = ("WHERE " + " AND ".join(conditions)) if conditions else ""

            total_row = conn.execute(
                f"SELECT COUNT(*) FROM power_events {where}", params
            ).fetchone()
            total = total_row[0] if total_row else 0

            rows = conn.execute(
                f"SELECT * FROM power_events {where} ORDER BY timestamp DESC LIMIT ? OFFSET ?",
                params + [page_size, offset],
            ).fetchall()

            items = [
                EventSchema(
                    id=row["id"],
                    timestamp=row["timestamp"],
                    device_id=row["device_id"],
                    event_type=row["event_type"],
                    metadata=json.loads(row["metadata"]) if row["metadata"] else {},
                )
                for row in rows
            ]
            return EventsPage(page=page, page_size=page_size, total=total, items=items)
    except sqlite3.OperationalError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=_DB_UNAVAILABLE,
        ) from exc
