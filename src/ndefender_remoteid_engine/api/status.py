from __future__ import annotations

from dataclasses import dataclass
from threading import Lock
from typing import Optional


@dataclass
class StatusSnapshot:
    timestamp_ms: int = 0
    state: str = "offline"
    contacts_active: int = 0
    mode: str = "live"
    last_update_ms: int = 0
    last_error: Optional[str] = None

    def to_dict(self) -> dict:
        payload = {
            "timestamp_ms": self.timestamp_ms,
            "state": self.state,
            "contacts_active": self.contacts_active,
            "mode": self.mode,
            "last_update_ms": self.last_update_ms,
        }
        if self.last_error:
            payload["last_error"] = self.last_error
        return payload


class StatusStore:
    def __init__(self) -> None:
        self._lock = Lock()
        self._snapshot = StatusSnapshot()
        self._contacts: dict[str, dict] = {}
        self._replay: dict[str, object] = {"active": False, "source": "none"}
        self._stats: dict[str, int] = {"frames": 0, "decoded": 0, "dropped": 0, "dedupe_hits": 0}

    def update_from_telemetry(self, event: dict) -> None:
        self.update_from_event(event)

    def update_from_event(self, event: dict) -> None:
        if not isinstance(event, dict):
            return
        event_type = event.get("type")
        data = event.get("data", {}) if isinstance(event.get("data"), dict) else {}
        ts = int(event.get("timestamp_ms") or 0)
        with self._lock:
            if event_type in {"CONTACT_NEW", "CONTACT_UPDATE"}:
                contact_id = data.get("id")
                if contact_id:
                    self._contacts[str(contact_id)] = data
            elif event_type == "CONTACT_LOST":
                contact_id = data.get("id")
                if contact_id:
                    self._contacts.pop(str(contact_id), None)
            if event_type == "REPLAY_STATE":
                state = str(data.get("state", "")).lower()
                active = state in {"start", "progress", "running"}
                self._replay = {"active": active, "source": "remoteid" if active else "none"}
                self._snapshot = StatusSnapshot(
                    timestamp_ms=ts or self._snapshot.timestamp_ms,
                    state="replay" if active else self._snapshot.state,
                    contacts_active=self._snapshot.contacts_active,
                    mode="replay" if active else self._snapshot.mode,
                    last_update_ms=ts or self._snapshot.last_update_ms,
                    last_error=self._snapshot.last_error,
                )
            if event_type == "TELEMETRY_UPDATE":
                last_ts = int(data.get("last_update_ms", data.get("last_ts", self._snapshot.last_update_ms)))
                self._snapshot = StatusSnapshot(
                    timestamp_ms=ts or self._snapshot.timestamp_ms,
                    state=str(data.get("state", self._snapshot.state)),
                    contacts_active=int(data.get("contacts_active", self._snapshot.contacts_active)),
                    mode=str(data.get("mode", self._snapshot.mode)),
                    last_update_ms=last_ts,
                    last_error=self._snapshot.last_error,
                )

    def snapshot(self) -> StatusSnapshot:
        with self._lock:
            return StatusSnapshot(**self._snapshot.__dict__)

    def contacts(self) -> list[dict]:
        with self._lock:
            return list(self._contacts.values())

    def replay_state(self) -> dict[str, object]:
        with self._lock:
            return dict(self._replay)

    def stats(self) -> dict[str, int]:
        with self._lock:
            return dict(self._stats)
