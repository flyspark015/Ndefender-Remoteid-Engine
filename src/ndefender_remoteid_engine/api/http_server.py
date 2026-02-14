from __future__ import annotations

import json
import threading
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Optional

from ndefender_remoteid_engine.api.status import StatusStore


class _StatusHandler(BaseHTTPRequestHandler):
    store: StatusStore

    def do_GET(self) -> None:  # noqa: N802
        if self.path not in ("/api/v1/status", "/api/v1/health"):
            self.send_response(404)
            self.end_headers()
            return

        snapshot = self.store.snapshot().to_dict()
        payload = json.dumps(snapshot).encode("utf-8")

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

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
