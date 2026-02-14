from ndefender_remoteid_engine.health import HealthMonitor


def test_health_states():
    health = HealthMonitor(interval_s=1.0, stale_after_s=2.0)

    event = health.maybe_emit(now_ms=1_000, contacts_active=0, mode="live")
    assert event is not None
    assert event["data"]["state"] == "offline"

    health.start()
    health.update_frame(1_000)
    event = health.maybe_emit(now_ms=2_000, contacts_active=1, mode="live")
    assert event is not None
    assert event["data"]["state"] == "ok"

    event = health.maybe_emit(now_ms=3_500, contacts_active=1, mode="live")
    assert event is not None
    assert event["data"]["state"] == "degraded"

    event = health.maybe_emit(now_ms=4_500, contacts_active=1, mode="replay")
    assert event is not None
    assert event["data"]["state"] == "replay"
