from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, Any

from ndefender_remoteid_engine.io.jsonl import append_jsonl

DEFAULT_LOG_PATH = "/opt/ndefender/logs/remoteid_engine.jsonl"


Event = Dict[str, Any]
EventSink = Callable[[Event], None]


def build_event(event_type: str, timestamp_ms: int, data: Dict[str, Any]) -> Event:
    return {
        "type": event_type,
        "timestamp_ms": int(timestamp_ms),
        "source": "remoteid",
        "data": data,
    }


@dataclass
class JsonlEmitter:
    path: str = DEFAULT_LOG_PATH

    def emit(self, event: Event) -> None:
        append_jsonl(self.path, event)


@dataclass
class SinkEmitter:
    sink: EventSink

    def emit(self, event: Event) -> None:
        self.sink(event)
