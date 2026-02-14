from ndefender_remoteid_engine.api.status import StatusStore


def test_status_store_update():
    store = StatusStore()
    event = {
        "type": "TELEMETRY_UPDATE",
        "timestamp": 1700000000000,
        "source": "remoteid",
        "data": {
            "state": "ok",
            "last_ts": 1700000000000,
            "contacts_active": 3,
            "mode": "live",
        },
    }
    store.update_from_telemetry(event)
    snapshot = store.snapshot()
    assert snapshot.state == "ok"
    assert snapshot.last_ts == 1700000000000
    assert snapshot.contacts_active == 3
    assert snapshot.mode == "live"
    assert snapshot.updated_ts == 1700000000000
