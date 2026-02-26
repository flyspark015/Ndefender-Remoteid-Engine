from __future__ import annotations

import json
import time
import threading
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Optional

from ndefender_remoteid_engine.api.status import StatusStore


class _StatusHandler(BaseHTTPRequestHandler):
    store: StatusStore

    def _send_json(self, status: int, payload: dict) -> None:
        data = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _send_error(self, status: int, detail: str) -> None:
        self._send_json(status, {"detail": detail})

    def do_GET(self) -> None:  # noqa: N802
        now_ms = int(time.time() * 1000)
        if self.path == "/api/v1/health":
            return self._send_json(200, {"status": "ok", "timestamp_ms": now_ms})
        if self.path == "/api/v1/status":
            snapshot = self.store.snapshot().to_dict()
            if not snapshot.get("timestamp_ms"):
                snapshot["timestamp_ms"] = now_ms
            return self._send_json(200, snapshot)
        if self.path == "/api/v1/contacts":
            return self._send_json(200, {"timestamp_ms": now_ms, "contacts": self.store.contacts()})
        if self.path == "/api/v1/stats":
            payload = {"timestamp_ms": now_ms, **self.store.stats()}
            return self._send_json(200, payload)
        if self.path == "/api/v1/replay/state":
            payload = {"timestamp_ms": now_ms, **self.store.replay_state()}
            return self._send_json(200, payload)
        self.send_response(404)
        self.end_headers()

    def do_POST(self) -> None:  # noqa: N802
        if self.path in (
            "/api/v1/monitor/start",
            "/api/v1/monitor/stop",
            "/api/v1/replay/start",
            "/api/v1/replay/stop",
        ):
            return self._send_error(409, "not_implemented")
        self.send_response(404)
        self.end_headers()

    def log_message(self, format: str, *args) -> None:  # noqa: A003
        return


@dataclass
class StatusHttpServer:
    host: str = "0.0.0.0"
    port: int = 9001
    store: StatusStore = field(default_factory=StatusStore)
    _server: Optional[ThreadingHTTPServer] = field(default=None, init=False)
    _thread: Optional[threading.Thread] = field(default=None, init=False)

    def start(self) -> None:
        if self._server is not None:
            return
        handler = type("StatusHandler", (_StatusHandler,), {"store": self.store})
        self._server = ThreadingHTTPServer((self.host, self.port), handler)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        if self._server is None:
            return
        self._server.shutdown()
        self._server.server_close()
        if self._thread:
            self._thread.join(timeout=5)
        self._server = None
        self._thread = None
