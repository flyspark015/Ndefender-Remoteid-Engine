# N-Defender RemoteID Engine - Technical Documentation

Last updated: 2026-02-15

## 1) System Architecture
The RemoteID engine is a modular Python package designed to capture, decode, deduplicate, and track RemoteID broadcasts, then emit canonical events for the N-Defender backend aggregator.

### Core Modules
- **Capture** (`capture/`)
  - `wifi_capture.py`: Live capture via monitor-mode interface and tshark EK JSONL output.
  - `replay_capture.py`: Deterministic replay from EK JSONL files.
- **Decode** (`decode/`)
  - `odid_parser.py`: Extracts OpenDroneID fields from EK JSONL “layers”.
  - `dedupe.py`: Windowed duplicate suppression.
- **Tracking** (`tracking/`)
  - `tracker.py`: Contact lifecycle rules and event emission.
  - `models.py`: Observation and contact state models.
- **Health** (`health.py`)
  - Telemetry state emission (`TELEMETRY_UPDATE`).
- **I/O** (`io/`)
  - `jsonl.py`: JSONL read/write utilities.
  - `emit.py`: Canonical envelope builder + emitters.
- **API** (`api/`)
  - `http_server.py`: Optional local `/api/v1/status` endpoint.
  - `server.py`: Backend WebSocket emitter.
- **Engine** (`engine.py`)
  - Live and replay orchestration.

### Runtime Dependencies
- `tshark` (live capture) with patched OpenDroneID Lua dissector.
- `gpsd` + `gpspipe` (optional GPS monitoring).
- Python 3.11+.

## 2) Data Flow (End-to-End)
1. **Capture**
   - Live: `WifiCapture` runs tshark → EK JSONL frames.
   - Replay: `ReplayCapture` reads EK JSONL file.
2. **Decode**
   - `OdidParser` produces `Observation` with:
     - `timestamp_ms`, `basic_id`, `mac`, `operator_id`, `model`, `lat`, `lon`, `altitude_m`, `speed_m_s`.
3. **De-duplication**
   - `DedupeFilter` suppresses duplicates within a 100 ms window.
4. **Tracking**
   - `ContactTracker` applies lifecycle rules and emits events.
5. **Emission**
   - Events are written to `/opt/ndefender/logs/remoteid_engine.jsonl`.
   - Optional WebSocket emission to backend.
6. **Health Telemetry**
   - Periodic `TELEMETRY_UPDATE` indicates state and contact count.

## 3) Replay Engine
Replay mode allows deterministic playback without hardware.

- Input: EK JSONL capture log.
- Timing: Uses record timestamp_ms values and a speed multiplier.
- Events: Emits `REPLAY_STATE` and contact events.
- Replay-only ID synthesis:
  - If `operator_id` exists but `basic_id` and `mac` do not, replay assigns `basic_id = "opid:<operator_id>"` to allow stable contact tracking.

CLI:
```bash
ndefender-remoteid replay --log /path/to/file.jsonl --speed 1.0 --emit-progress
```

## 4) Contact Tracking Logic
### Stable ID Priority
1. `basic_id` → `rid:<basic_id>`
2. `mac` → `rid:mac:<mac>`
3. Otherwise: no contact emitted.

### Confirmation Gating
- `CONTACT_NEW` emitted only after `min_frames_to_confirm` (default 2).

### Update Policy
- `CONTACT_UPDATE` emitted when:
  - `update_interval_s` elapsed, or
  - `lat/lon` changes, or
  - `operator_id` changes.

### Lost Policy
- `CONTACT_LOST` emitted once after `ttl_s` (default 15s).
- Contact is removed from active map after LOST.

### Duplicate NEW
- Not allowed without LOST between lifecycles.

## 5) De-duplication Logic
- Window-based suppression (default window: 100 ms).
- Keyed by:
  - `basic_id`, `mac`, `operator_id`, `model`, `lat`, `lon`, `altitude_m`, `speed_m_s`.
- Prevents repeated EK frames from inflating contact updates.

## 6) GPS Integration
- Optional monitoring via `gpspipe` to obtain TPV fixes.
- Current usage: polled alongside capture loop.
- Future integration: fuse GPS fix quality into operational telemetry and/or operator location correlation.

## 7) API Contracts
### REST (Engine-local status)
If `api.enabled: true`, the engine exposes:

- `GET /api/v1/status`
- `GET /api/v1/health`

Response:
```json
{
  "state": "ok",
  "last_ts": 1700000000000,
  "contacts_active": 3,
  "mode": "live",
  "updated_ts": 1700000000000
}
```

### WebSocket (Backend emission)
If `backend.enabled: true`, the engine emits canonical events to:
```
ws://<backend-host>:8000/api/v1/ws
```

## 8) Event Models
All events use the canonical envelope:
```json
{
  "type": "CONTACT_NEW",
  "timestamp_ms": 1700000000000,
  "source": "remoteid",
  "data": { }
}
```

Allowed event types:
- `CONTACT_NEW`
- `CONTACT_UPDATE`
- `CONTACT_LOST`
- `TELEMETRY_UPDATE`
- `REPLAY_STATE`

### Contact events (`CONTACT_NEW/UPDATE/LOST`)
```json
{
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
```

### Telemetry event (`TELEMETRY_UPDATE`)
```json
{
  "state": "ok",
  "last_ts": 1700000000000,
  "contacts_active": 3,
  "mode": "live"
}
```

### Replay state (`REPLAY_STATE`)
```json
{
  "state": "progress",
  "speed": 1.0,
  "position": 42,
  "ts": 1700000000000
}
```

## 9) Operational Workflow
1. Start engine (systemd or CLI).
2. Live capture or replay produces observations.
3. Dedupe + tracker emit canonical events.
4. Events logged to `/opt/ndefender/logs/remoteid_engine.jsonl`.
5. Optional backend WebSocket emission.
6. Backend tails JSONL and merges into `/api/v1/status` contacts.

## 10) Configuration
`config/default.yaml`:
- `capture.interface`: monitor interface (e.g. `mon0`)
- `tracker.ttl_s`, `tracker.min_frames_to_confirm`, `tracker.update_interval_s`
- `replay.speed`
- `telemetry.interval_s`, `telemetry.stale_after_s`
- `backend.enabled`, `backend.ws_url`
- `api.enabled`, `api.host`, `api.port`

## 10.1) Capture Interface Bring-Up (mon0)
Create and validate monitor interface:
```bash
iw dev
sudo iw phy phy1 interface add mon0 type monitor
sudo ip link set mon0 up
ip link show mon0 || true
```

Minimal capture checks:
```bash
sudo tshark -i mon0 -a duration:5 -c 20
sudo tshark -i mon0 -a duration:8 -Y opendroneid -T fields -e OpenDroneID.basicID_id_asc 2>/dev/null | head
```

Notes:
- You will not see ODID frames unless a nearby drone is broadcasting.
- If tshark exits, the engine now logs the error and retries with a short backoff.

## 11) Validation & Testing
Key tests:
- Contact confirmation
- No double NEW
- LOST after TTL
- Dedupe logic
- Replay mode
- Schema validation

Verification commands:
```bash
pytest -q
python -m compileall -q src
ndefender-remoteid validate --log /opt/ndefender/logs/remoteid_engine.jsonl
```

## 12) Technical Suggestions
- Add BLE capture path and unify with WiFi pipeline.
- Add formal metrics export (Prometheus) for contacts/latency/health.
- Add configurable log rotation or log size guardrails.
- Add telemetry for decode error rates and dedupe drop counts.

## 13) Required Improvements
- Introduce GPS fix quality gating (mode >= 2) before location fusion.
- Add explicit replay speed normalization for near-zero time deltas.
- Add per-contact update throttling under extreme event rates.

## 14) Production Hardening Recommendations
- Systemd watchdog and restart policies with bounded backoff.
- Disk usage monitoring for `/opt/ndefender/logs`.
- Periodic log rotation and archive retention.
- Health endpoint probe for monitoring stack.
- Add alarms for stale telemetry and excessive event rates.
