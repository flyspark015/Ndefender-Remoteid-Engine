from ndefender_remoteid_engine.tracking.models import Observation
from ndefender_remoteid_engine.tracking.tracker import ContactTracker


def test_contact_confirmation():
    tracker = ContactTracker(min_frames_to_confirm=2, update_interval_s=1.0, ttl_s=15)

    events = tracker.process_observation(
        Observation(timestamp_ms=1_000, basic_id="ABC123")
    )
    assert events == []

    events = tracker.process_observation(
        Observation(timestamp_ms=1_100, basic_id="ABC123")
    )
    assert len(events) == 1
    assert events[0]["type"] == "CONTACT_NEW"
    assert events[0]["data"]["id"] == "rid:ABC123"


def test_no_double_new():
    tracker = ContactTracker(min_frames_to_confirm=2, update_interval_s=1.0, ttl_s=15)

    tracker.process_observation(Observation(timestamp_ms=1_000, basic_id="ABC123"))
    events = tracker.process_observation(
        Observation(timestamp_ms=1_100, basic_id="ABC123")
    )
    assert [event["type"] for event in events] == ["CONTACT_NEW"]

    events = tracker.process_observation(
        Observation(timestamp_ms=1_150, basic_id="ABC123")
    )
    assert events == []


def test_lost_after_ttl():
    tracker = ContactTracker(min_frames_to_confirm=2, update_interval_s=1.0, ttl_s=1)

    tracker.process_observation(Observation(timestamp_ms=1_000, basic_id="ABC123"))
    tracker.process_observation(Observation(timestamp_ms=1_100, basic_id="ABC123"))

    events = tracker.sweep(now_ms=2_200)
    assert len(events) == 1
    assert events[0]["type"] == "CONTACT_LOST"
    assert tracker.active_contacts() == 0
