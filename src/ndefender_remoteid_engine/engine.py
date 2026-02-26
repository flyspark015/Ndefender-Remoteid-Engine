from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Optional

from ndefender_remoteid_engine.api.http_server import StatusHttpServer
from ndefender_remoteid_engine.api.server import BackendEmitter, CompositeEmitter
from ndefender_remoteid_engine.api.status import StatusStore
from ndefender_remoteid_engine.capture.replay_capture import ReplayCapture
from ndefender_remoteid_engine.capture.wifi_capture import WifiCapture
from ndefender_remoteid_engine.config import AppConfig, ReplayConfig, TelemetryConfig, TrackerConfig
from ndefender_remoteid_engine.decode.dedupe import DedupeFilter
from ndefender_remoteid_engine.decode.odid_parser import OdidParser
from ndefender_remoteid_engine.events.validate import validate_event
from ndefender_remoteid_engine.fusion.gps import GpsMonitor
from ndefender_remoteid_engine.health import HealthMonitor
from ndefender_remoteid_engine.io.emit import JsonlEmitter, SinkEmitter
from ndefender_remoteid_engine.tracking.tracker import ContactTracker


CaptureFactory = Callable[[], object]


def build_default_emitter(config: AppConfig) -> CompositeEmitter:
    emitters: list[object] = [JsonlEmitter()]
    if config.backend.enabled:
        emitters.append(
            BackendEmitter(
                ws_url=config.backend.ws_url,
                reconnect_s=config.backend.reconnect_s,
                ping_interval_s=config.backend.ping_interval_s,
                queue_max=config.backend.queue_max,
            )
        )
    return CompositeEmitter(emitters)


@dataclass
class ReplayEngine:
    log_path: str
    config: AppConfig = field(default_factory=AppConfig)
    emitter: JsonlEmitter | SinkEmitter | CompositeEmitter = field(default=None)
    validate_events: bool = False
    emit_progress: bool = False

    _parser: OdidParser = field(default_factory=OdidParser, init=False)
    _dedupe: DedupeFilter = field(default_factory=DedupeFilter, init=False)
    _tracker: ContactTracker = field(init=False)
    _health: HealthMonitor = field(init=False)
    _gps: Optional[GpsMonitor] = field(default=None, init=False)
    _last_ts: Optional[int] = field(default=None, init=False)
    _status_store: Optional[StatusStore] = field(default=None, init=False)
    _status_server: Optional[StatusHttpServer] = field(default=None, init=False)

    def __post_init__(self) -> None:
        tracker_cfg: TrackerConfig = self.config.tracker
        telemetry_cfg: TelemetryConfig = self.config.telemetry

        if self.emitter is None:
            self.emitter = build_default_emitter(self.config)

        self._tracker = ContactTracker(
            ttl_s=tracker_cfg.ttl_s,
            min_frames_to_confirm=tracker_cfg.min_frames_to_confirm,
            update_interval_s=tracker_cfg.update_interval_s,
        )
        self._health = HealthMonitor(
            interval_s=telemetry_cfg.interval_s,
            stale_after_s=telemetry_cfg.stale_after_s,
        )
        if self.config.gps.enabled:
            self._gps = GpsMonitor()
        if self.config.api.enabled:
            self._status_store = StatusStore()
            self._status_server = StatusHttpServer(
                host=self.config.api.host,
                port=self.config.api.port,
                store=self._status_store,
            )

    def _emit(self, event: dict) -> None:
        if self.validate_events:
            validate_event(event)
        self.emitter.emit(event)
        if self._status_store is not None:
            self._status_store.update_from_event(event)

    def _emit_telemetry(self, now_ms: int) -> None:
        telemetry = self._health.maybe_emit(
            now_ms=now_ms,
            contacts_active=self._tracker.active_contacts(),
            mode="replay",
        )
        if telemetry:
            self._emit(telemetry)
            if self._status_store is not None:
                self._status_store.update_from_telemetry(telemetry)

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
        if self._status_server is not None:
            self._status_server.start()

        def handler(obs) -> None:
            if not self._dedupe.accept(obs):
                return
            self._last_ts = obs.timestamp_ms
            self._health.update_frame(obs.timestamp_ms)
            if self._gps is not None:
                _ = self._gps.poll_once()

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
        if self._status_server is not None:
            self._status_server.stop()
        stop_fn = getattr(self.emitter, "stop", None)
        if stop_fn:
            stop_fn()


@dataclass
class LiveEngine:
    config: AppConfig = field(default_factory=AppConfig)
    emitter: JsonlEmitter | SinkEmitter | CompositeEmitter = field(default=None)
    validate_events: bool = False
    capture_factory: Optional[Callable[[], WifiCapture]] = None

    _parser: OdidParser = field(default_factory=OdidParser, init=False)
    _dedupe: DedupeFilter = field(default_factory=DedupeFilter, init=False)
    _tracker: ContactTracker = field(init=False)
    _health: HealthMonitor = field(init=False)
    _gps: Optional[GpsMonitor] = field(default=None, init=False)
    _last_ts: Optional[int] = field(default=None, init=False)
    _status_store: Optional[StatusStore] = field(default=None, init=False)
    _status_server: Optional[StatusHttpServer] = field(default=None, init=False)

    def __post_init__(self) -> None:
        tracker_cfg: TrackerConfig = self.config.tracker
        telemetry_cfg: TelemetryConfig = self.config.telemetry

        if self.emitter is None:
            self.emitter = build_default_emitter(self.config)

        self._tracker = ContactTracker(
            ttl_s=tracker_cfg.ttl_s,
            min_frames_to_confirm=tracker_cfg.min_frames_to_confirm,
            update_interval_s=tracker_cfg.update_interval_s,
        )
        self._health = HealthMonitor(
            interval_s=telemetry_cfg.interval_s,
            stale_after_s=telemetry_cfg.stale_after_s,
        )
        if self.config.gps.enabled:
            self._gps = GpsMonitor()
        if self.config.api.enabled:
            self._status_store = StatusStore()
            self._status_server = StatusHttpServer(
                host=self.config.api.host,
                port=self.config.api.port,
                store=self._status_store,
            )

    def _emit(self, event: dict) -> None:
        if self.validate_events:
            validate_event(event)
        self.emitter.emit(event)
        if self._status_store is not None:
            self._status_store.update_from_event(event)

    def _emit_telemetry(self, now_ms: int) -> None:
        telemetry = self._health.maybe_emit(
            now_ms=now_ms,
            contacts_active=self._tracker.active_contacts(),
            mode="live",
        )
        if telemetry:
            self._emit(telemetry)
            if self._status_store is not None:
                self._status_store.update_from_telemetry(telemetry)

    def run(self) -> None:
        capture = self.capture_factory() if self.capture_factory else WifiCapture(
            interface=self.config.capture.interface
        )
        self._health.start()
        if self._status_server is not None:
            self._status_server.start()

        try:
            for record in capture.iter_records():
                obs = self._parser.parse_record(record)
                if obs is None:
                    continue
                if not self._dedupe.accept(obs):
                    continue
                self._last_ts = obs.timestamp_ms
                self._health.update_frame(obs.timestamp_ms)
                if self._gps is not None:
                    _ = self._gps.poll_once()

                for event in self._tracker.process_observation(obs):
                    self._emit(event)
                for event in self._tracker.sweep(now_ms=obs.timestamp_ms):
                    self._emit(event)
                self._emit_telemetry(obs.timestamp_ms)
        except KeyboardInterrupt:
            pass
        finally:
            if isinstance(capture, WifiCapture):
                capture.stop()

        if self._last_ts is not None:
            flush_ts = self._last_ts + int(self._tracker.ttl_s * 1000) + 1
            for event in self._tracker.sweep(now_ms=flush_ts):
                self._emit(event)
            self._emit_telemetry(flush_ts)

        self._health.stop()
        if self._status_server is not None:
            self._status_server.stop()
        stop_fn = getattr(self.emitter, "stop", None)
        if stop_fn:
            stop_fn()
