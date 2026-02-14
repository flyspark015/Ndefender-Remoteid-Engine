# N-Defender RemoteID Contact Detection & Tracking Engine

Modular WiFi/BLE-based RemoteID capture, decode, contact lifecycle tracking, replay framework, and canonical backend event emission engine for N-Defender.

## Quick Start

### Install
```bash
python -m venv .venv
. .venv/bin/activate
pip install -e .
```

### Run (Live)
```bash
ndefender-remoteid run --config config/default.yaml
```

### Run (Replay)
```bash
ndefender-remoteid replay --log /opt/ndefender/logs/odid_wifi_sample.ek.jsonl --config config/default.yaml --speed 1.0
```

### Validate Engine Output (JSONL)
```bash
ndefender-remoteid validate --log /opt/ndefender/logs/remoteid_engine.jsonl
```

## Configuration
See `config/default.yaml` for all settings.

Key sections:
- `capture.interface`: monitor-mode interface for tshark (e.g., `mon0`).
- `tracker.*`: TTL and confirmation settings for contacts.
- `replay.speed`: playback speed multiplier.
- `telemetry.*`: telemetry emission interval and stale thresholds.
- `backend.*`: optional WebSocket emission to backend aggregator.
- `api.*`: optional local status API (`/api/v1/status`).

## Output Contract
All events are emitted in canonical envelope:
```json
{
  "type": "CONTACT_NEW",
  "timestamp": 1700000000000,
  "source": "remoteid",
  "data": {
    "id": "rid:123456",
    "type": "REMOTE_ID",
    "model": "DJI Mini 3",
    "operator_id": "ABC123",
    "lat": 23.0225,
    "lon": 72.5714,
    "altitude_m": 120.0,
    "speed_m_s": 12.5,
    "last_seen_ts": 1700000000000
  }
}
```

## Logs
Engine output is always written to:
```
/opt/ndefender/logs/remoteid_engine.jsonl
```

## Development
```bash
pytest -q
python -m compileall -q src
```
