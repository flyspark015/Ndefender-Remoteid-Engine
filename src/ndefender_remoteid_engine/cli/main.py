import argparse
import sys
from collections import Counter

from ndefender_remoteid_engine.config import AppConfig, load_config
from ndefender_remoteid_engine.engine import ReplayEngine
from ndefender_remoteid_engine.events.validate import validate_event
from ndefender_remoteid_engine.io.jsonl import read_jsonl
from ndefender_remoteid_engine.version import __version__


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ndefender-remoteid",
        description="N-Defender RemoteID Contact Detection & Tracking Engine",
    )
    parser.add_argument("--version", action="version", version=__version__)

    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Run live capture/track engine")
    run_parser.add_argument("--config", required=True, help="Path to config YAML")

    replay_parser = subparsers.add_parser("replay", help="Replay EK JSONL log")
    replay_parser.add_argument("--log", required=True, help="Path to EK JSONL log")
    replay_parser.add_argument("--config", help="Path to config YAML")
    replay_parser.add_argument("--speed", type=float, help="Replay speed multiplier")
    replay_parser.add_argument("--emit-progress", action="store_true", help="Emit replay progress events")

    validate_parser = subparsers.add_parser("validate", help="Validate EK JSONL log")
    validate_parser.add_argument("--log", required=True, help="Path to EK JSONL log")

    stats_parser = subparsers.add_parser("stats", help="Compute stats from EK JSONL log")
    stats_parser.add_argument("--log", required=True, help="Path to EK JSONL log")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command == "run":
        print("run: live capture not implemented yet")
        return 2
    if args.command == "replay":
        if args.config:
            cfg = load_config(args.config)
        else:
            cfg = AppConfig()
        engine = ReplayEngine(
            log_path=args.log,
            config=cfg,
            emit_progress=args.emit_progress,
        )
        engine.run(speed_override=args.speed)
        return 0
    if args.command == "validate":
        total = 0
        for event in read_jsonl(args.log):
            validate_event(event)
            total += 1
        print(f"validate: ok ({total} events)")
        return 0
    if args.command == "stats":
        counts: Counter[str] = Counter()
        total = 0
        for event in read_jsonl(args.log):
            event_type = event.get("type", "UNKNOWN")
            counts[event_type] += 1
            total += 1
        print(f"stats: total={total}")
        for event_type, count in counts.most_common():
            print(f"{event_type}: {count}")
        return 0

    parser.error("unknown command")
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
