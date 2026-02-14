import pytest

from ndefender_remoteid_engine.events.validate import validate_event


def test_schema_validation():
    event = {
        "type": "CONTACT_NEW",
        "timestamp": 1700000000000,
        "source": "remoteid",
        "data": {
            "id": "rid:123",
            "type": "REMOTE_ID",
            "last_seen_ts": 1700000000000,
        },
    }
    validate_event(event)

    bad_event = {
        "type": "CONTACT_NEW",
        "timestamp": 1700000000000,
        "source": "remoteid",
        "data": {
            "id": "rid:123",
            "type": "REMOTE_ID",
            "last_seen_ts": 1700000000000,
            "lat": 123.0,
        },
    }
    with pytest.raises(ValueError):
        validate_event(bad_event)
