from ndefender_remoteid_engine.fusion.gps import parse_tpv


def test_parse_tpv():
    payload = {
        "class": "TPV",
        "time": "2026-01-01T00:00:00.000Z",
        "lat": 45.0,
        "lon": -122.0,
        "altMSL": 100.5,
        "speed": 12.3,
        "mode": 3,
    }
    fix = parse_tpv(payload)
    assert fix is not None
    assert fix.lat == 45.0
    assert fix.lon == -122.0
    assert fix.alt_m == 100.5
    assert fix.speed_m_s == 12.3
    assert fix.mode == 3

    assert parse_tpv({"class": "SKY"}) is None
