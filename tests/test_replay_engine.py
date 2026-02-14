from __future__ import annotations

import json

from ndefender_remoteid_engine.config import AppConfig, ReplayConfig, TelemetryConfig, TrackerConfig
from ndefender_remoteid_engine.engine import ReplayEngine
from ndefender_remoteid_engine.io.emit import SinkEmitter


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


def test_replay_engine_emits_contact_and_telemetry(tmp_path):
    path = tmp_path / "replay.jsonl"
    records = [
        _ek_record(1_000, "RID-123"),
        _ek_record(1_200, "RID-123"),
    ]
    with path.open("w", encoding="utf-8") as fh:
        for record in records:
            fh.write(json.dumps(record) + "\n")

    events: list[dict] = []
    emitter = SinkEmitter(events.append)

    cfg = AppConfig(
        tracker=TrackerConfig(min_frames_to_confirm=2, update_interval_s=10.0, ttl_s=1),
        replay=ReplayConfig(speed=10.0),
        telemetry=TelemetryConfig(interval_s=0.0, stale_after_s=1.0),
    )
    engine = ReplayEngine(log_path=str(path), config=cfg, emitter=emitter)
    engine.run()

    event_types = [event["type"] for event in events]
    assert "CONTACT_NEW" in event_types
    assert "REPLAY_STATE" in event_types
