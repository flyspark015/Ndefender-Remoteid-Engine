from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class Observation:
    timestamp_ms: int
    basic_id: Optional[str] = None
    mac: Optional[str] = None
    operator_id: Optional[str] = None
    model: Optional[str] = None
    lat: Optional[float] = None
    lon: Optional[float] = None
    altitude_m: Optional[float] = None
    speed_m_s: Optional[float] = None
    frame_ts_ms: Optional[int] = None


@dataclass
class ContactState:
    contact_id: str
    first_seen_ts: int
    last_seen_ts: int
    frames_seen: int = 0
    confirmed: bool = False
    last_emit_ts: Optional[int] = None
    model: Optional[str] = None
    operator_id: Optional[str] = None
    lat: Optional[float] = None
    lon: Optional[float] = None
    altitude_m: Optional[float] = None
    speed_m_s: Optional[float] = None
    last_emitted_lat: Optional[float] = None
    last_emitted_lon: Optional[float] = None
    last_emitted_operator_id: Optional[str] = None

    def update_from_observation(self, obs: Observation) -> None:
        self.last_seen_ts = obs.timestamp_ms
        if obs.model is not None:
            self.model = obs.model
        if obs.operator_id is not None:
            self.operator_id = obs.operator_id
        if obs.lat is not None:
            self.lat = obs.lat
        if obs.lon is not None:
            self.lon = obs.lon
        if obs.altitude_m is not None:
            self.altitude_m = obs.altitude_m
        if obs.speed_m_s is not None:
            self.speed_m_s = obs.speed_m_s

    def to_contact_data(self) -> dict[str, object]:
        data: dict[str, object] = {
            "id": self.contact_id,
            "type": "REMOTE_ID",
            "last_seen_ts": self.last_seen_ts,
        }
        if self.model is not None:
            data["model"] = self.model
        if self.operator_id is not None:
            data["operator_id"] = self.operator_id
        if self.lat is not None and self.lon is not None:
            data["lat"] = self.lat
            data["lon"] = self.lon
        if self.altitude_m is not None:
            data["altitude_m"] = self.altitude_m
        if self.speed_m_s is not None:
            data["speed_m_s"] = self.speed_m_s
        return data
