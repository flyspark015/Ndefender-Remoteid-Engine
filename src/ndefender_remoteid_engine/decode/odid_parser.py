from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Iterable, Optional

from ndefender_remoteid_engine.tracking.models import Observation


_MAC_RE = re.compile(r"(?:[0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}")


def _as_list(value: Any) -> list:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _to_int(value: Any) -> Optional[int]:
    if value is None:
        return None
    if isinstance(value, list):
        value = value[0] if value else None
    if value is None:
        return None
    try:
        return int(str(value), 10)
    except (TypeError, ValueError):
        return None


def _to_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, list):
        value = value[0] if value else None
    if value is None:
        return None
    try:
        return float(str(value))
    except (TypeError, ValueError):
        return None


def _find_mac(value: Any) -> Optional[str]:
    if isinstance(value, dict):
        for inner in value.values():
            match = _find_mac(inner)
            if match:
                return match
        return None
    if isinstance(value, list):
        for inner in value:
            match = _find_mac(inner)
            if match:
                return match
        return None
    if isinstance(value, str):
        match = _MAC_RE.search(value)
        if match:
            return match.group(0)
    return None


def _lat_from_raw(raw: Optional[int]) -> Optional[float]:
    if raw is None:
        return None
    if raw in (2147483647, -2147483648):
        return None
    return raw / 1e7


def _lon_from_raw(raw: Optional[int]) -> Optional[float]:
    if raw is None:
        return None
    if raw in (2147483647, -2147483648):
        return None
    return raw / 1e7


def _alt_from_raw(raw: Optional[int]) -> Optional[float]:
    if raw is None:
        return None
    if raw in (32767, -32768):
        return None
    return raw / 10.0


def _speed_from_raw(raw: Optional[int]) -> Optional[float]:
    if raw is None:
        return None
    if raw in (255,):
        return None
    return raw * 0.25


@dataclass
class OdidParser:
    def parse_record(self, record: dict[str, Any]) -> Optional[Observation]:
        timestamp_ms = _to_int(record.get("timestamp"))
        layers = record.get("layers", {})

        if timestamp_ms is None:
            frame = layers.get("frame", {})
            epoch = _to_float(frame.get("frame_frame_time_epoch"))
            if epoch is not None:
                timestamp_ms = int(epoch * 1000)

        if timestamp_ms is None:
            return None

        mac = _find_mac(layers)
        operator_id = None
        basic_id = None
        model = None
        lat = None
        lon = None
        altitude_m = None
        speed_m_s = None

        for entry in _as_list(layers.get("opendroneid")):
            if not isinstance(entry, dict):
                continue
            msg_pack = entry.get("opendroneid_message_pack", {})
            if not isinstance(msg_pack, dict):
                continue

            operator_msg = msg_pack.get("opendroneid_message_operatorid")
            if isinstance(operator_msg, dict):
                operator_id = operator_msg.get("opendroneid_OpenDroneID_operator_id", operator_id)

            location_msg = msg_pack.get("opendroneid_message_location")
            if isinstance(location_msg, dict):
                lat_raw = _to_int(location_msg.get("opendroneid_OpenDroneID_loc_lat"))
                lon_raw = _to_int(location_msg.get("opendroneid_OpenDroneID_loc_lon"))
                alt_raw = _to_int(location_msg.get("opendroneid_OpenDroneID_loc_geoAlt"))
                speed_raw = _to_int(location_msg.get("opendroneid_OpenDroneID_loc_speed"))
                lat = _lat_from_raw(lat_raw) or lat
                lon = _lon_from_raw(lon_raw) or lon
                altitude_m = _alt_from_raw(alt_raw) or altitude_m
                speed_m_s = _speed_from_raw(speed_raw) or speed_m_s

            self_id_msg = msg_pack.get("opendroneid_message_selfid")
            if isinstance(self_id_msg, dict):
                model = self_id_msg.get("opendroneid_OpenDroneID_self_desc", model)

            basic_msg = msg_pack.get("opendroneid_message_basicid")
            if isinstance(basic_msg, dict):
                basic_id = (
                    basic_msg.get("opendroneid_OpenDroneID_basic_id")
                    or basic_msg.get("opendroneid_OpenDroneID_basic_id_id")
                    or basic_msg.get("opendroneid_OpenDroneID_basic_id_str")
                    or basic_id
                )

        if not any([operator_id, basic_id, mac, lat, lon, model]):
            return None

        return Observation(
            timestamp_ms=timestamp_ms,
            basic_id=basic_id,
            mac=mac,
            operator_id=operator_id,
            model=model,
            lat=lat,
            lon=lon,
            altitude_m=altitude_m,
            speed_m_s=speed_m_s,
            frame_ts_ms=timestamp_ms,
        )

    def iter_observations(self, records: Iterable[dict[str, Any]]) -> Iterable[Observation]:
        for record in records:
            obs = self.parse_record(record)
            if obs is not None:
                yield obs
