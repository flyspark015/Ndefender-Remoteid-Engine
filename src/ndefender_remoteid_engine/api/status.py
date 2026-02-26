from __future__ import annotations

from dataclasses import dataclass
from threading import Lock
from typing import Optional


@dataclass
class StatusSnapshot:
    state: str = "offline"
    last_ts: int = 0
    contacts_active: int = 0
    mode: str = "live"
    updated_ts: int = 0

    def to_dict(self) -> dict:
        return {
            "state": self.state,
            "last_ts": self.last_ts,
            "contacts_active": self.contacts_active,
            "mode": self.mode,
            "updated_ts": self.updated_ts,
        }


class StatusStore:
    def __init__(self) -> None:
        self._lock = Lock()
        self._snapshot = StatusSnapshot()

    def update_from_telemetry(self, event: dict) -> None:
        data = event.get("data", {}) if isinstance(event, dict) else {}
        with self._lock:
            self._snapshot = StatusSnapshot(
                state=str(data.get("state", self._snapshot.state)),
                last_ts=int(data.get("last_ts", self._snapshot.last_ts)),
                contacts_active=int(data.get("contacts_active", self._snapshot.contacts_active)),
                mode=str(data.get("mode", self._snapshot.mode)),
                updated_ts=int(
                    event.get(
                        "timestamp_ms",
                        event.get("timestamp", self._snapshot.updated_ts),
                    )
                ),
            )

    def snapshot(self) -> StatusSnapshot:
        with self._lock:
            return StatusSnapshot(**self._snapshot.__dict__)
