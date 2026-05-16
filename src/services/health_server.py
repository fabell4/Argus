"""Lightweight HTTP health server running in a daemon thread."""
from __future__ import annotations

import json
import logging
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any, Callable

_LOG = logging.getLogger(__name__)


class HealthServer:
    """Serves GET /health on a background thread."""

    def __init__(self, port: int = 9100, status_fn: Callable[[], dict[str, Any]] | None = None) -> None:
        self._port = port
        self._status_fn = status_fn or (lambda: {"status": "ok"})
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        handler_factory = self._make_handler
        server = HTTPServer(("0.0.0.0", self._port), handler_factory)  # noqa: S104

        self._thread = threading.Thread(target=server.serve_forever, daemon=True)
        self._thread.start()
        _LOG.info("Health server listening on port %d.", self._port)

    def _make_handler(self, *args: Any, **kwargs: Any) -> "_HealthHandler":
        return _HealthHandler(self._status_fn, *args, **kwargs)


class _HealthHandler(BaseHTTPRequestHandler):
    def __init__(
        self,
        status_fn: Callable[[], dict[str, Any]],
        *args: Any,
        **kwargs: Any,
    ) -> None:
        self._status_fn = status_fn
        super().__init__(*args, **kwargs)

    def do_GET(self) -> None:  # noqa: N802
        if self.path != "/health":
            self.send_response(404)
            self.end_headers()
            return

        status = self._status_fn()
        code = 200 if status.get("status") == "ok" else 503
        body = json.dumps(status).encode()

        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt: str, *args: Any) -> None:  # noqa: ANN401  # pylint: disable=arguments-differ
        """Suppress default HTTP access logging."""
