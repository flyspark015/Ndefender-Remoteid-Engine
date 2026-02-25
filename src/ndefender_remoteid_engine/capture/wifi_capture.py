from __future__ import annotations

import json
import logging
import subprocess
import time
from dataclasses import dataclass, field
from typing import Iterable, Iterator, Optional

logger = logging.getLogger(__name__)


@dataclass
class WifiCapture:
    interface: str
    tshark_path: str = "tshark"
    extra_args: list[str] = field(default_factory=list)
    retry_delay_s: float = 5.0

    _proc: Optional[subprocess.Popen[str]] = field(default=None, init=False)

    def _build_command(self) -> list[str]:
        return [
            self.tshark_path,
            "-i",
            self.interface,
            "-l",
            "-T",
            "ek",
            *self.extra_args,
        ]

    def start(self) -> None:
        if self._proc is not None:
            return
        cmd = self._build_command()
        logger.info("starting tshark: %s", " ".join(cmd))
        self._proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )

    def stop(self) -> None:
        if self._proc is None:
            return
        proc = self._proc
        self._proc = None
        logger.info("stopping tshark")
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=5)

    def iter_records(self) -> Iterator[dict]:
        while True:
            self.start()
            assert self._proc is not None
            assert self._proc.stdout is not None
            assert self._proc.stderr is not None

            for line in self._proc.stdout:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    logger.debug("failed to parse EK JSON line")
                    continue
                if isinstance(record, dict):
                    yield record

            stderr_output = self._proc.stderr.read().strip()
            returncode = self._proc.wait()
            self._proc = None
            if returncode not in (0, None):
                logger.error("tshark exited with %s: %s", returncode, stderr_output)
                time.sleep(self.retry_delay_s)
                continue
            break

    def __enter__(self) -> "WifiCapture":
        self.start()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.stop()
