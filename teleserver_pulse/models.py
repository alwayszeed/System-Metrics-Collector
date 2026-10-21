"""Typed containers for metrics collected by Teleserver Pulse."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(slots=True)
class DiskMetrics:
    path: str
    total_bytes: int
    used_bytes: int
    free_bytes: int
    percent: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class SystemMetrics:
    timestamp: str
    hostname: str
    platform: str
    cpu_percent: float
    cpu_count: int
    load_average: list[float] | None
    memory_total_bytes: int
    memory_used_bytes: int
    memory_available_bytes: int
    memory_percent: float
    swap_percent: float
    uptime_seconds: float
    disks: list[DiskMetrics] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["disks"] = [disk.to_dict() for disk in self.disks]
        return data


@dataclass(slots=True)
class ContainerMetrics:
    id: str
    name: str
    image: str
    status: str
    state: str
    cpu_percent: float
    memory_usage_bytes: int
    memory_limit_bytes: int
    memory_percent: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class CollectionResult:
    system: SystemMetrics
    containers: list[ContainerMetrics]
    docker_error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "system": self.system.to_dict(),
            "containers": [container.to_dict() for container in self.containers],
            "docker_error": self.docker_error,
        }
