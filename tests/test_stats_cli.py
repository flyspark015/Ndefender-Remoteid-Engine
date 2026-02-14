from __future__ import annotations

import json

from ndefender_remoteid_engine.cli.main import main


def _event(event_type: str, ts: int, contact_id: str | None = None) -> dict:
    data = {"last_seen_ts": ts, "type": "REMOTE_ID"}
    if contact_id is not None:
        data["id"] = contact_id
    return {
        "type": event_type,
        "timestamp": ts,
        "source": "remoteid",
        "data": data,
    }


def test_stats_cli_outputs_counts(tmp_path, capsys):
    path = tmp_path / "events.jsonl"
    events = [
        _event("CONTACT_NEW", 1_000, "rid:1"),
        _event("CONTACT_UPDATE", 2_000, "rid:1"),
        _event("CONTACT_LOST", 3_000, "rid:1"),
    ]
    with path.open("w", encoding="utf-8") as fh:
        for event in events:
            fh.write(json.dumps(event) + "\n")

    assert main(["stats", "--log", str(path)]) == 0
    output = capsys.readouterr().out
    assert "stats: total=3" in output
    assert "CONTACT_NEW: 1" in output
    assert "CONTACT_UPDATE: 1" in output
    assert "CONTACT_LOST: 1" in output
    assert "unique_contacts: 1" in output
