from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, List, Optional

from ndefender_remoteid_engine.api.contract import (
    CONTACT_TYPE_REMOTE_ID,
    EVENT_CONTACT_LOST,
    EVENT_CONTACT_NEW,
    EVENT_CONTACT_UPDATE,
)
from ndefender_remoteid_engine.io.emit import build_event
from ndefender_remoteid_engine.tracking.models import ContactState, Observation


NowProvider = Callable[[], int]


def _derive_contact_id(obs: Observation) -> str:
    if obs.basic_id:
        return f"rid:{obs.basic_id}"
    if obs.mac:
        return f"rid:mac:{obs.mac}"
    if obs.operator_id:
        return f"rid:op:{obs.operator_id}"
    anonymous = "anon"
    return f"rid:{anonymous}"


@dataclass
class ContactTracker:
    ttl_s: int = 15
    min_frames_to_confirm: int = 2
    update_interval_s: float = 1.0
    now_provider: Optional[NowProvider] = None

    def __post_init__(self) -> None:
        if self.min_frames_to_confirm < 1:
            raise ValueError("min_frames_to_confirm must be >= 1")
        if self.ttl_s <= 0:
            raise ValueError("ttl_s must be > 0")
        if self.update_interval_s < 0:
            raise ValueError("update_interval_s must be >= 0")
        self._contacts: Dict[str, ContactState] = {}

    def _now_ms(self) -> int:
        if self.now_provider is None:
            raise RuntimeError("now_provider is required when timestamps are missing")
        return int(self.now_provider())

    def process_observation(self, obs: Observation) -> List[dict]:
        if obs.timestamp_ms is None:
            obs_ts = self._now_ms()
            obs = Observation(**{**obs.__dict__, "timestamp_ms": obs_ts})

        contact_id = _derive_contact_id(obs)
        state = self._contacts.get(contact_id)
        if state is None:
            state = ContactState(
                contact_id=contact_id,
                first_seen_ts=obs.timestamp_ms,
                last_seen_ts=obs.timestamp_ms,
                frames_seen=0,
            )
            self._contacts[contact_id] = state

        state.frames_seen += 1
        state.update_from_observation(obs)

        events: List[dict] = []

        if not state.confirmed:
            if state.frames_seen >= self.min_frames_to_confirm:
                state.confirmed = True
                state.last_emit_ts = obs.timestamp_ms
                state.last_emitted_lat = state.lat
                state.last_emitted_lon = state.lon
                state.last_emitted_operator_id = state.operator_id
                data = state.to_contact_data()
                data["type"] = CONTACT_TYPE_REMOTE_ID
                events.append(build_event(EVENT_CONTACT_NEW, obs.timestamp_ms, data))
            return events

        should_update = False
        if state.last_emit_ts is None:
            should_update = True
        else:
            elapsed_ms = obs.timestamp_ms - state.last_emit_ts
            if elapsed_ms >= int(self.update_interval_s * 1000):
                should_update = True

        lat_changed = (
            state.lat is not None
            and state.lon is not None
            and (state.lat != state.last_emitted_lat or state.lon != state.last_emitted_lon)
        )
        operator_changed = (
            state.operator_id is not None
            and state.operator_id != state.last_emitted_operator_id
        )

        if lat_changed or operator_changed:
            should_update = True

        if should_update:
            state.last_emit_ts = obs.timestamp_ms
            state.last_emitted_lat = state.lat
            state.last_emitted_lon = state.lon
            state.last_emitted_operator_id = state.operator_id
            data = state.to_contact_data()
            data["type"] = CONTACT_TYPE_REMOTE_ID
            events.append(build_event(EVENT_CONTACT_UPDATE, obs.timestamp_ms, data))

        return events

    def sweep(self, now_ms: Optional[int] = None) -> List[dict]:
        if now_ms is None:
            now_ms = self._now_ms()
        events: List[dict] = []
        expired: List[str] = []
        ttl_ms = int(self.ttl_s * 1000)
        for contact_id, state in self._contacts.items():
            if now_ms - state.last_seen_ts > ttl_ms:
                data = {
                    "id": state.contact_id,
                    "type": CONTACT_TYPE_REMOTE_ID,
                    "last_seen_ts": state.last_seen_ts,
                }
                events.append(build_event(EVENT_CONTACT_LOST, now_ms, data))
                expired.append(contact_id)

        for contact_id in expired:
            del self._contacts[contact_id]

        return events

    def active_contacts(self) -> int:
        return len(self._contacts)
