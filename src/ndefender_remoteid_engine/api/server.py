from __future__ import annotations

import asyncio
import json
import queue
import threading
import time
from dataclasses import dataclass, field
from typing import Optional

import websockets


@dataclass
class BackendEmitter:
    ws_url: str
    reconnect_s: float = 5.0
    ping_interval_s: float = 20.0
    queue_max: int = 1000

    _queue: queue.Queue[str] = field(init=False)
    _thread: Optional[threading.Thread] = field(default=None, init=False)
    _stop: threading.Event = field(default_factory=threading.Event, init=False)
    _started: bool = field(default=False, init=False)

    def __post_init__(self) -> None:
        self._queue = queue.Queue(maxsize=self.queue_max)

    def start(self) -> None:
        if self._started:
            return
        self._started = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=5)

    def emit(self, event: dict) -> None:
        if not self._started:
            self.start()
        payload = json.dumps(event, separators=(",", ":"))
        try:
            self._queue.put_nowait(payload)
        except queue.Full:
            try:
                _ = self._queue.get_nowait()
                self._queue.put_nowait(payload)
            except queue.Full:
                pass
            except queue.Empty:
                pass

    def _run(self) -> None:
        asyncio.run(self._run_async())

    async def _run_async(self) -> None:
        while not self._stop.is_set():
            try:
                async with websockets.connect(
                    self.ws_url, ping_interval=self.ping_interval_s
                ) as ws:
                    while not self._stop.is_set():
                        try:
                            payload = await asyncio.to_thread(self._queue.get, True, 0.5)
                        except queue.Empty:
                            continue
                        await ws.send(payload)
            except Exception:
                await asyncio.sleep(self.reconnect_s)


class CompositeEmitter:
    def __init__(self, emitters: list[object]) -> None:
        self._emitters = emitters

    def emit(self, event: dict) -> None:
        for emitter in self._emitters:
            emit_fn = getattr(emitter, "emit", None)
            if emit_fn:
                emit_fn(event)

    def stop(self) -> None:
        for emitter in self._emitters:
            stop_fn = getattr(emitter, "stop", None)
            if stop_fn:
                stop_fn()
