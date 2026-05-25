"""GET /api/diagnostics — last poll diagnostics from shared state."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from src import shared_state

router = APIRouter(tags=["diagnostics"])


@router.get("/diagnostics")
def get_diagnostics() -> dict[str, Any]:
    return shared_state.get_last_diagnostics()
