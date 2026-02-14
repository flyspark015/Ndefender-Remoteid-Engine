from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from ndefender_remoteid_engine.api.contract import EVENT_TELEMETRY_UPDATE
from ndefender_remoteid_engine.io.emit import build_event


@dataclass
class HealthMonitor:
    interval_s: float = 1.0
    stale_after_s: float = 5.0
    running: bool = False
    last_frame_ts: Optional[int] = None
    last_emit_ts: Optional[int] = None

    def start(self) -> None:
        self.running = True

    def stop(self) -> None:
        self.running = False

    def update_frame(self, timestamp_ms: int) -> None:
        self.last_frame_ts = timestamp_ms

    def _state(self, now_ms: int, mode: str) -> str:
        if mode == "replay":
            return "replay"
        if not self.running:
            return "offline"
        if self.last_frame_ts is None:
            return "degraded"
        stale_ms = int(self.stale_after_s * 1000)
        if now_ms - self.last_frame_ts <= stale_ms:
            return "ok"
        return "degraded"

    def maybe_emit(self, now_ms: int, contacts_active: int, mode: str) -> Optional[dict]:
        if self.interval_s <= 0:
            return None
        interval_ms = int(self.interval_s * 1000)
        if self.last_emit_ts is None or now_ms - self.last_emit_ts >= interval_ms:
            self.last_emit_ts = now_ms
            data = {
                "state": self._state(now_ms, mode),
                "last_ts": self.last_frame_ts or 0,
                "contacts_active": int(contacts_active),
                "mode": mode,
            }
            return build_event(EVENT_TELEMETRY_UPDATE, now_ms, data)
        return None
