from __future__ import annotations

import json
import logging
import subprocess
from dataclasses import dataclass
from typing import Iterator, Optional

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class GpsFix:
    timestamp: Optional[str] = None
    lat: Optional[float] = None
    lon: Optional[float] = None
    alt_m: Optional[float] = None
    speed_m_s: Optional[float] = None
    mode: Optional[int] = None


def _to_float(value: object) -> Optional[float]:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _to_int(value: object) -> Optional[int]:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def parse_tpv(payload: dict) -> Optional[GpsFix]:
    if payload.get("class") != "TPV":
        return None
    return GpsFix(
        timestamp=payload.get("time"),
        lat=_to_float(payload.get("lat")),
        lon=_to_float(payload.get("lon")),
        alt_m=_to_float(payload.get("altMSL")) or _to_float(payload.get("alt")),
        speed_m_s=_to_float(payload.get("speed")),
        mode=_to_int(payload.get("mode")),
    )


class GpsMonitor:
    def __init__(self, gpspipe_path: str = "gpspipe") -> None:
        self._gpspipe_path = gpspipe_path

    def poll_once(self) -> Optional[GpsFix]:
        cmd = [self._gpspipe_path, "-w", "-n", "1"]
        try:
            result = subprocess.run(
                cmd,
                check=False,
                capture_output=True,
                text=True,
                timeout=5,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            logger.warning("gps poll failed: %s", exc)
            return None

        if result.returncode != 0:
            logger.warning("gpspipe exited with %s", result.returncode)
            return None

        for line in result.stdout.splitlines():
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            fix = parse_tpv(payload)
            if fix is not None:
                return fix
        return None

    def iter_fixes(self) -> Iterator[GpsFix]:
        cmd = [self._gpspipe_path, "-w"]
        try:
            with subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
            ) as proc:
                assert proc.stdout is not None
                for line in proc.stdout:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        payload = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    fix = parse_tpv(payload)
                    if fix is not None:
                        yield fix
        except OSError as exc:
            logger.warning("gps stream failed: %s", exc)
