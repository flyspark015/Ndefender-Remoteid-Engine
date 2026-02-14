# N-Defender RemoteID Engine Progress

## ✅ What has been completed
- Project skeleton with modular package layout, config, and CLI scaffolding.
- Canonical event schema and JSONL utilities with validation.
- Contact lifecycle tracker with confirmation gating, updates, and TTL loss handling.
- Dedupe filter for duplicate EK frames.
- Replay capture and replay engine with deterministic speed control.
- Live capture pipeline using tshark EK JSON streaming.
- Health state machine with TELEMETRY_UPDATE emission.
- Backend WebSocket emitter with reconnect and queueing + composite logging emitter.
- CI workflow (tests, schema validation, compile check).
- GPS fusion module (gpsd via gpspipe) with TPV parsing.

## 🟡 What is currently in progress
- None (ready for next phase selection).

## ❌ What is pending
- Optional API service layer for status/health exposure.
- CLI enhancements for engine log validation/stats beyond generic JSONL.
- Production usage/deployment documentation.

## 🧪 Verification results
- `pytest -q` -> `10 passed in 0.46s`
- `python -m compileall -q src` -> success
- Schema validation quick check -> `schema ok`

## 🧩 Test outcomes
- Lifecycle tests: confirmation, no double NEW, LOST after TTL.
- Replay tests: deterministic replay, REPLAY_STATE emission.
- Engine tests: replay engine and live engine coverage.
- GPS parsing test: TPV parsing and non-TPV rejection.

## 📦 Code changes implemented
- `src/ndefender_remoteid_engine/decode/odid_parser.py`
- `src/ndefender_remoteid_engine/decode/dedupe.py`
- `src/ndefender_remoteid_engine/tracking/models.py`
- `src/ndefender_remoteid_engine/tracking/tracker.py`
- `src/ndefender_remoteid_engine/capture/replay_capture.py`
- `src/ndefender_remoteid_engine/capture/wifi_capture.py`
- `src/ndefender_remoteid_engine/fusion/gps.py`
- `src/ndefender_remoteid_engine/health.py`
- `src/ndefender_remoteid_engine/engine.py`
- `src/ndefender_remoteid_engine/api/server.py`
- `src/ndefender_remoteid_engine/events/schema.json`
- `src/ndefender_remoteid_engine/events/validate.py`
- `src/ndefender_remoteid_engine/io/jsonl.py`
- `src/ndefender_remoteid_engine/io/emit.py`
- `config/default.yaml`
- `.github/workflows/ci.yml`
- `tests/*`

## 🧠 Key decisions taken
- Enforced stable ID priority: basic_id > mac, with no fallback to operator ID.
- Delayed CONTACT_NEW until confirmation frames threshold is met.
- Emission policy: update interval or location/operator changes trigger UPDATE.
- Canonical schema enforcement with strict additionalProperties false.
- Composite emitter always logs to JSONL and optionally streams to backend WS.
- GPS fusion is optional and non-blocking (uses gpspipe, best-effort).
