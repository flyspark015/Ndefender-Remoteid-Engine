from __future__ import annotations

import json

from ndefender_remoteid_engine.capture.replay_capture import ReplayCapture
from ndefender_remoteid_engine.tracking.models import Observation


def _ek_record(timestamp_ms: int, operator_id: str | None = None, lat: float | None = None, lon: float | None = None) -> dict:
    opendroneid = []
    if operator_id is not None:
        opendroneid.append(
            {
                "opendroneid_message_pack": {
                    "opendroneid_message_operatorid": {
                        "opendroneid_OpenDroneID_operator_id": operator_id,
                    }
                }
            }
        )
    if lat is not None and lon is not None:
        opendroneid.append(
            {
                "opendroneid_message_pack": {
                    "opendroneid_message_location": {
                        "opendroneid_OpenDroneID_loc_lat": str(int(lat * 1e7)),
                        "opendroneid_OpenDroneID_loc_lon": str(int(lon * 1e7)),
                        "opendroneid_OpenDroneID_loc_geoAlt": "250",
                        "opendroneid_OpenDroneID_loc_speed": "40",
                    }
                }
            }
        )
    return {
        "timestamp": str(timestamp_ms),
        "layers": {
            "frame": {"frame_frame_time_epoch": str(timestamp_ms / 1000.0)},
            "opendroneid": opendroneid,
        },
    }


def test_replay_mode(tmp_path):
    path = tmp_path / "replay.jsonl"
    records = [
        _ek_record(1_000, operator_id="GBR-OP-123ABCD"),
        _ek_record(2_000, lat=45.0, lon=-122.0),
    ]
    with path.open("w", encoding="utf-8") as fh:
        for record in records:
            fh.write(json.dumps(record) + "\n")

    sleep_calls: list[float] = []
    observations: list[Observation] = []
    state_events: list[dict] = []

    def fake_sleep(delay: float) -> None:
        sleep_calls.append(delay)

    capture = ReplayCapture(
        path=str(path),
        speed=2.0,
        sleep_fn=fake_sleep,
        state_sink=state_events.append,
        emit_progress=True,
    )
    capture.run(observations.append)

    assert len(observations) == 2
    assert observations[0].operator_id == "GBR-OP-123ABCD"
    assert observations[1].lat == 45.0
    assert observations[1].lon == -122.0

    assert sleep_calls == [0.5]
    assert state_events[0]["type"] == "REPLAY_STATE"
    assert state_events[-1]["data"]["state"] == "done"
