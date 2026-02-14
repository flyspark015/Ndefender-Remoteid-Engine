from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable, Iterator


def read_jsonl(path: str | Path) -> Iterator[dict[str, Any]]:
    file_path = Path(path)
    with file_path.open("r", encoding="utf-8") as fh:
        for lineno, line in enumerate(fh, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"invalid JSON at line {lineno}: {exc.msg}"
                ) from exc
            if not isinstance(obj, dict):
                raise ValueError(f"expected object at line {lineno}")
            yield obj


def write_jsonl(path: str | Path, items: Iterable[dict[str, Any]], append: bool = False) -> None:
    file_path = Path(path)
    mode = "a" if append else "w"
    with file_path.open(mode, encoding="utf-8") as fh:
        for item in items:
            fh.write(json.dumps(item, separators=(",", ":")) + "\n")


def append_jsonl(path: str | Path, item: dict[str, Any]) -> None:
    write_jsonl(path, [item], append=True)
