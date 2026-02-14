from ndefender_remoteid_engine.decode.dedupe import DedupeFilter
from ndefender_remoteid_engine.tracking.models import Observation


def test_dedupe_logic():
    dedupe = DedupeFilter(window_ms=100)
    obs = Observation(timestamp_ms=1_000, basic_id="ABC123", lat=1.0, lon=2.0)

    assert dedupe.accept(obs) is True
    assert dedupe.accept(obs) is False

    obs_next = Observation(timestamp_ms=1_200, basic_id="ABC123", lat=1.0, lon=2.0)
    assert dedupe.accept(obs_next) is True
