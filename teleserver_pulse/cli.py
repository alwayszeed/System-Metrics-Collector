"""Command line interface for Teleserver Pulse metrics collection."""

from __future__ import annotations

import argparse
import json
import sys

from .metrics import collect_all, human_bytes, missing_docker_binary


def _print_pretty(result) -> None:
    system = result.system
    print(f"Host      : {system.hostname} ({system.platform})")
    print(f"Timestamp : {system.timestamp}")
    print(f"CPU       : {system.cpu_percent:.1f}% across {system.cpu_count} logical cores")
    if system.load_average:
        print(f"Load avg  : {system.load_average}")
    print(
        f"Memory    : {system.memory_percent:.1f}% "
        f"({human_bytes(system.memory_used_bytes)} / {human_bytes(system.memory_total_bytes)})"
    )
    print(f"Swap      : {system.swap_percent:.1f}%")
    print(f"Uptime    : {system.uptime_seconds / 3600:.1f} hours")
    for disk in system.disks:
        print(
            f"Disk {disk.path:<10}: {disk.percent:.1f}% "
            f"({human_bytes(disk.used_bytes)} / {human_bytes(disk.total_bytes)})"
        )

    print(f"\nContainers: {len(result.containers)}")
    for container in result.containers:
        print(
            f"  - {container.name} [{container.image}] {container.state} "
            f"cpu={container.cpu_percent:.1f}% mem={container.memory_percent:.1f}%"
        )
    if result.docker_error:
        print(f"\nDocker note: {result.docker_error}")
        if result.docker_error != "Container collection disabled." and missing_docker_binary():
            print("Hint: install Docker Desktop/Engine so the `docker` binary is on PATH.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="teleserver-pulse",
        description="Collect system hardware and Docker container metrics.",
    )
    parser.add_argument("--json", action="store_true", help="Print a JSON document instead of a table.")
    parser.add_argument("--no-docker", action="store_true", help="Skip Docker container collection.")
    parser.add_argument("--disk", default=None, help="Disk path/mountpoint to measure (default: / or C:\\).")
    parser.add_argument("--pretty", action="store_true", help="Force human-readable output (default).")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        result = collect_all(args.disk, include_containers=not args.no_docker)
    except Exception as exc:  # pragma: no cover - CLI guard
        print(f"Failed to collect metrics: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(result.to_dict(), indent=2))
    else:
        _print_pretty(result)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
