from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class CaptureConfig:
    interface: str = "mon0"


@dataclass
class TrackerConfig:
    ttl_s: int = 15
    min_frames_to_confirm: int = 2
    update_interval_s: float = 1.0


@dataclass
class ReplayConfig:
    speed: float = 1.0


@dataclass
class GpsConfig:
    enabled: bool = True


@dataclass
class TelemetryConfig:
    interval_s: float = 1.0
    stale_after_s: float = 5.0


@dataclass
class BackendConfig:
    enabled: bool = False
    ws_url: str = "ws://127.0.0.1:8000/api/v1/ws"
    reconnect_s: float = 5.0
    ping_interval_s: float = 20.0
    queue_max: int = 1000


@dataclass
class ApiConfig:
    enabled: bool = False
    host: str = "0.0.0.0"
    port: int = 9001


@dataclass
class AppConfig:
    capture: CaptureConfig = field(default_factory=CaptureConfig)
    tracker: TrackerConfig = field(default_factory=TrackerConfig)
    replay: ReplayConfig = field(default_factory=ReplayConfig)
    gps: GpsConfig = field(default_factory=GpsConfig)
    telemetry: TelemetryConfig = field(default_factory=TelemetryConfig)
    backend: BackendConfig = field(default_factory=BackendConfig)
    api: ApiConfig = field(default_factory=ApiConfig)


def _load_yaml(path: str | Path) -> dict[str, Any]:
    file_path = Path(path)
    with file_path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    if not isinstance(data, dict):
        raise ValueError("config root must be a mapping")
    return data


def load_config(path: str | Path) -> AppConfig:
    data = _load_yaml(path)

    capture = data.get("capture", {})
    tracker = data.get("tracker", {})
    replay = data.get("replay", {})
    gps = data.get("gps", {})
    telemetry = data.get("telemetry", {})
    backend = data.get("backend", {})
    api = data.get("api", {})

    return AppConfig(
        capture=CaptureConfig(interface=str(capture.get("interface", "mon0"))),
        tracker=TrackerConfig(
            ttl_s=int(tracker.get("ttl_s", 15)),
            min_frames_to_confirm=int(tracker.get("min_frames_to_confirm", 2)),
            update_interval_s=float(tracker.get("update_interval_s", 1.0)),
        ),
        replay=ReplayConfig(speed=float(replay.get("speed", 1.0))),
        gps=GpsConfig(enabled=bool(gps.get("enabled", True))),
        telemetry=TelemetryConfig(
            interval_s=float(telemetry.get("interval_s", 1.0)),
            stale_after_s=float(telemetry.get("stale_after_s", 5.0)),
        ),
        backend=BackendConfig(
            enabled=bool(backend.get("enabled", False)),
            ws_url=str(backend.get("ws_url", "ws://127.0.0.1:8000/api/v1/ws")),
            reconnect_s=float(backend.get("reconnect_s", 5.0)),
            ping_interval_s=float(backend.get("ping_interval_s", 20.0)),
            queue_max=int(backend.get("queue_max", 1000)),
        ),
        api=ApiConfig(
            enabled=bool(api.get("enabled", False)),
            host=str(api.get("host", "0.0.0.0")),
            port=int(api.get("port", 9001)),
        ),
    )
