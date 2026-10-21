"""Collect system metrics with psutil and container metrics with the Docker SDK.

Docker is an optional dependency at runtime: when the daemon or SDK is not
available, collection still succeeds and reports the reason via `docker_error`.
"""

from __future__ import annotations

import os
import platform
import shutil
import socket
import time
from datetime import datetime, timezone

import psutil

from .models import CollectionResult, ContainerMetrics, DiskMetrics, SystemMetrics

try:  # Docker SDK is optional for hosts without containers.
    import docker
    from docker.errors import DockerException
except ImportError:  # pragma: no cover - exercised only when SDK is absent
    docker = None  # type: ignore[assignment]

    class DockerException(Exception):  # type: ignore[no-redef]
        """Fallback so callers can keep a single except clause."""


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_average() -> list[float] | None:
    if not hasattr(os, "getloadavg"):
        return None
    try:
        return [round(value, 2) for value in os.getloadavg()]
    except OSError:  # pragma: no cover - uncommon platform edge case
        return None


def collect_system_metrics(disk_path: str | None = None, *, sample_interval: float = 0.5) -> SystemMetrics:
    """Collect CPU, memory, swap, uptime and disk usage.

    `psutil.cpu_percent` needs an interval to produce a meaningful value on the
    first call, hence the short blocking sample.
    """
    disk_path = disk_path or ("C:\\" if os.name == "nt" else "/")
    memory = psutil.virtual_memory()
    swap = psutil.swap_memory()
    disk = psutil.disk_usage(disk_path)

    disks = [
        DiskMetrics(
            path=disk_path,
            total_bytes=disk.total,
            used_bytes=disk.used,
            free_bytes=disk.free,
            percent=round(disk.percent, 2),
        )
    ]
    if os.name != "nt":
        seen = {disk_path}
        for partition in psutil.disk_partitions(all=False):
            if partition.mountpoint in seen:
                continue
            try:
                usage = psutil.disk_usage(partition.mountpoint)
            except (PermissionError, OSError):
                continue
            seen.add(partition.mountpoint)
            disks.append(
                DiskMetrics(
                    path=partition.mountpoint,
                    total_bytes=usage.total,
                    used_bytes=usage.used,
                    free_bytes=usage.free,
                    percent=round(usage.percent, 2),
                )
            )

    return SystemMetrics(
        timestamp=_now_iso(),
        hostname=socket.gethostname(),
        platform=f"{platform.system()} {platform.release()}",
        cpu_percent=round(psutil.cpu_percent(interval=sample_interval), 2),
        cpu_count=psutil.cpu_count(logical=True) or 1,
        load_average=_load_average(),
        memory_total_bytes=memory.total,
        memory_used_bytes=memory.used,
        memory_available_bytes=memory.available,
        memory_percent=round(memory.percent, 2),
        swap_percent=round(swap.percent, 2),
        uptime_seconds=round(time.time() - psutil.boot_time(), 2),
        disks=disks,
    )


def _container_cpu_percent(stats: dict) -> float:
    """Derive CPU usage percentage from one Docker stats sample."""
    try:
        cpu = stats["cpu_stats"]
        previous = stats["precpu_stats"]
        cpu_delta = cpu["cpu_usage"]["total_usage"] - previous["cpu_usage"]["total_usage"]
        system_delta = cpu["system_cpu_usage"] - previous.get("system_cpu_usage", 0)
        online_cpus = cpu.get("online_cpus") or len(cpu["cpu_usage"].get("percpu_usage") or []) or 1
        if cpu_delta > 0 and system_delta > 0:
            return round((cpu_delta / system_delta) * online_cpus * 100.0, 2)
    except (KeyError, TypeError):
        pass
    return 0.0


def _container_memory(stats: dict) -> tuple[int, int, float]:
    memory = stats.get("memory_stats") or {}
    usage = int(memory.get("usage") or 0)
    # Docker includes the page cache on Linux; subtract it when available.
    cache = int((memory.get("stats") or {}).get("cache") or 0)
    usage = max(usage - cache, 0)
    limit = int(memory.get("limit") or 0)
    percent = round((usage / limit) * 100.0, 2) if limit else 0.0
    return usage, limit, percent


def collect_containers() -> tuple[list[ContainerMetrics], str | None]:
    """Return metrics for all containers plus an optional daemon error message."""
    if docker is None:
        return [], "Docker SDK is not installed (pip install docker)."

    try:
        client = docker.from_env()
    except DockerException as exc:
        return [], f"Cannot connect to Docker daemon: {exc}"

    containers: list[ContainerMetrics] = []
    try:
        for container in client.containers.list(all=True):
            try:
                stats = container.stats(stream=False)
                cpu_percent = _container_cpu_percent(stats)
                used, limit, memory_percent = _container_memory(stats)
            except Exception:  # stats can fail for stopped containers
                cpu_percent = 0.0
                used, limit, memory_percent = 0, 0, 0.0

            containers.append(
                ContainerMetrics(
                    id=container.short_id,
                    name=container.name,
                    image=(container.image.tags or [container.image.short_id])[0],
                    status=container.status,
                    state=(container.attrs.get("State") or {}).get("Status", container.status),
                    cpu_percent=cpu_percent,
                    memory_usage_bytes=used,
                    memory_limit_bytes=limit,
                    memory_percent=memory_percent,
                )
            )
    except DockerException as exc:
        return containers, f"Docker API error: {exc}"
    finally:
        try:
            client.close()
        except Exception:  # pragma: no cover - best effort cleanup
            pass

    containers.sort(key=lambda item: item.name.lower())
    return containers, None


def collect_all(disk_path: str | None = None, *, include_containers: bool = True) -> CollectionResult:
    system = collect_system_metrics(disk_path)
    if not include_containers:
        return CollectionResult(system=system, containers=[], docker_error="Container collection disabled.")
    containers, docker_error = collect_containers()
    return CollectionResult(system=system, containers=containers, docker_error=docker_error)


def human_bytes(value: int) -> str:
    """Format a byte count for CLI readability."""
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if abs(value) < 1024 or unit == "TiB":
            return f"{value:.1f} {unit}" if unit != "B" else f"{value} B"
        value /= 1024
    return f"{value} B"


def missing_docker_binary() -> bool:
    """True when the `docker` executable is not on PATH (useful for hints)."""
    return shutil.which("docker") is None


__all__ = [
    "collect_all",
    "collect_containers",
    "collect_system_metrics",
    "human_bytes",
    "missing_docker_binary",
]
