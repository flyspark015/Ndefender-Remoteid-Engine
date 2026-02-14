from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from ndefender_remoteid_engine.capture.replay_capture import ReplayCapture
from ndefender_remoteid_engine.config import AppConfig, ReplayConfig, TelemetryConfig, TrackerConfig
from ndefender_remoteid_engine.decode.dedupe import DedupeFilter
from ndefender_remoteid_engine.decode.odid_parser import OdidParser
from ndefender_remoteid_engine.events.validate import validate_event
from ndefender_remoteid_engine.health import HealthMonitor
from ndefender_remoteid_engine.io.emit import JsonlEmitter, SinkEmitter
from ndefender_remoteid_engine.tracking.tracker import ContactTracker


@dataclass
class ReplayEngine:
    log_path: str
    config: AppConfig = field(default_factory=AppConfig)
    emitter: JsonlEmitter | SinkEmitter = field(default_factory=JsonlEmitter)
    validate_events: bool = False
    emit_progress: bool = False

    _parser: OdidParser = field(default_factory=OdidParser, init=False)
    _dedupe: DedupeFilter = field(default_factory=DedupeFilter, init=False)
    _tracker: ContactTracker = field(init=False)
    _health: HealthMonitor = field(init=False)
    _last_ts: Optional[int] = field(default=None, init=False)

    def __post_init__(self) -> None:
        tracker_cfg: TrackerConfig = self.config.tracker
        telemetry_cfg: TelemetryConfig = self.config.telemetry

        self._tracker = ContactTracker(
            ttl_s=tracker_cfg.ttl_s,
            min_frames_to_confirm=tracker_cfg.min_frames_to_confirm,
            update_interval_s=tracker_cfg.update_interval_s,
        )
        self._health = HealthMonitor(
            interval_s=telemetry_cfg.interval_s,
            stale_after_s=telemetry_cfg.stale_after_s,
        )

    def _emit(self, event: dict) -> None:
        if self.validate_events:
            validate_event(event)
        self.emitter.emit(event)

    def _emit_telemetry(self, now_ms: int) -> None:
        telemetry = self._health.maybe_emit(
            now_ms=now_ms,
            contacts_active=self._tracker.active_contacts(),
            mode="replay",
        )
        if telemetry:
            self._emit(telemetry)

    def run(self, speed_override: Optional[float] = None) -> None:
        replay_cfg: ReplayConfig = self.config.replay
        speed = speed_override if speed_override is not None else replay_cfg.speed
        capture = ReplayCapture(
            path=self.log_path,
            speed=speed,
            parser=self._parser,
            state_sink=self._emit,
            emit_progress=self.emit_progress,
        )

        self._health.start()

        def handler(obs) -> None:
            if not self._dedupe.accept(obs):
                return
            self._last_ts = obs.timestamp_ms
            self._health.update_frame(obs.timestamp_ms)

            for event in self._tracker.process_observation(obs):
                self._emit(event)
            for event in self._tracker.sweep(now_ms=obs.timestamp_ms):
                self._emit(event)

            self._emit_telemetry(obs.timestamp_ms)

        capture.run(handler)

        if self._last_ts is not None:
            flush_ts = self._last_ts + int(self._tracker.ttl_s * 1000) + 1
            for event in self._tracker.sweep(now_ms=flush_ts):
                self._emit(event)
            self._emit_telemetry(flush_ts)

        self._health.stop()
