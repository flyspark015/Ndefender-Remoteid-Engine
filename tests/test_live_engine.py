from __future__ import annotations

import json

from ndefender_remoteid_engine.config import AppConfig, TelemetryConfig, TrackerConfig
from ndefender_remoteid_engine.engine import LiveEngine
from ndefender_remoteid_engine.io.emit import SinkEmitter


class FakeCapture:
    def __init__(self, records):
        self._records = records

    def iter_records(self):
        for record in self._records:
            yield record


def _ek_record(timestamp_ms: int, basic_id: str) -> dict:
    return {
        "timestamp": str(timestamp_ms),
        "layers": {
            "frame": {"frame_frame_time_epoch": str(timestamp_ms / 1000.0)},
            "opendroneid": [
                {
                    "opendroneid_message_pack": {
                        "opendroneid_message_basicid": {
                            "opendroneid_OpenDroneID_basic_id": basic_id,
                        }
                    }
                }
            ],
        },
    }


def test_live_engine_emits_contact():
    records = [
        _ek_record(1_000, "RID-123"),
        _ek_record(1_200, "RID-123"),
    ]
    events: list[dict] = []
    engine = LiveEngine(
        config=AppConfig(
            tracker=TrackerConfig(min_frames_to_confirm=2, update_interval_s=10.0, ttl_s=1),
            telemetry=TelemetryConfig(interval_s=0.0, stale_after_s=1.0),
        ),
        emitter=SinkEmitter(events.append),
        capture_factory=lambda: FakeCapture(records),
    )
    engine.run()

    event_types = [event["type"] for event in events]
    assert "CONTACT_NEW" in event_types
