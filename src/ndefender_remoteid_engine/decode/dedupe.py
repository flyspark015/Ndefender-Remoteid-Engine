from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Set

from ndefender_remoteid_engine.tracking.models import Observation


def _observation_key(obs: Observation) -> str:
    return "|".join(
        [
            obs.basic_id or "",
            obs.mac or "",
            obs.operator_id or "",
            obs.model or "",
            "" if obs.lat is None else f"{obs.lat:.7f}",
            "" if obs.lon is None else f"{obs.lon:.7f}",
            "" if obs.altitude_m is None else f"{obs.altitude_m:.3f}",
            "" if obs.speed_m_s is None else f"{obs.speed_m_s:.3f}",
        ]
    )


@dataclass
class DedupeFilter:
    window_ms: int = 100
    _buckets: Dict[int, Set[str]] = field(default_factory=dict)

    def _bucket_id(self, obs: Observation) -> int:
        ts = obs.frame_ts_ms if obs.frame_ts_ms is not None else obs.timestamp_ms
        if ts is None:
            return 0
        return int(ts // self.window_ms)

    def accept(self, obs: Observation) -> bool:
        bucket_id = self._bucket_id(obs)
        key = _observation_key(obs)
        bucket = self._buckets.setdefault(bucket_id, set())
        if key in bucket:
            return False
        bucket.add(key)
        self._cleanup(bucket_id)
        return True

    def _cleanup(self, current_bucket: int) -> None:
        cutoff = current_bucket - 2
        stale = [bucket_id for bucket_id in self._buckets if bucket_id < cutoff]
        for bucket_id in stale:
            del self._buckets[bucket_id]
