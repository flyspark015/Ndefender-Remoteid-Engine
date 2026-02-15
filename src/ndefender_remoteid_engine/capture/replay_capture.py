from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Callable, Iterable, Optional

from ndefender_remoteid_engine.api.contract import EVENT_REPLAY_STATE
from ndefender_remoteid_engine.decode.odid_parser import OdidParser
from ndefender_remoteid_engine.io.emit import build_event
from ndefender_remoteid_engine.io.jsonl import read_jsonl
from ndefender_remoteid_engine.tracking.models import Observation


SleepFn = Callable[[float], None]
ReplayStateSink = Callable[[dict], None]
ObservationHandler = Callable[[Observation], None]


@dataclass
class ReplayCapture:
    path: str
    speed: float = 1.0
    parser: OdidParser = field(default_factory=OdidParser)
    sleep_fn: SleepFn = time.sleep
    state_sink: Optional[ReplayStateSink] = None
    emit_progress: bool = False

    def iter_observations(self) -> Iterable[Observation]:
        for record in read_jsonl(self.path):
            obs = self.parser.parse_record(record)
            if obs is None:
                continue
            if obs.operator_id and not obs.basic_id and not obs.mac:
                # Replay logs sometimes only include operator_id. Synthesize a stable ID
                # for replay-only contact tracking to avoid dropping all observations.
                obs = Observation(**{**obs.__dict__, "basic_id": f"opid:{obs.operator_id}"})
            yield obs

    def _emit_state(self, state: str, speed: float, position: int, ts_ms: Optional[int]) -> None:
        if self.state_sink is None:
            return
        data = {"state": state, "speed": speed, "position": position}
        if ts_ms is not None:
            data["ts"] = int(ts_ms)
        self.state_sink(build_event(EVENT_REPLAY_STATE, int(time.time() * 1000), data))

    def run(self, handler: ObservationHandler) -> None:
        if self.speed <= 0:
            raise ValueError("speed must be > 0")

        position = 0
        prev_ts: Optional[int] = None
        self._emit_state("start", self.speed, position, None)

        for obs in self.iter_observations():
            position += 1
            if prev_ts is not None:
                delta_ms = obs.timestamp_ms - prev_ts
                if delta_ms > 0:
                    self.sleep_fn(delta_ms / 1000.0 / self.speed)
            handler(obs)
            prev_ts = obs.timestamp_ms
            if self.emit_progress:
                self._emit_state("progress", self.speed, position, obs.timestamp_ms)

        self._emit_state("done", self.speed, position, prev_ts)
