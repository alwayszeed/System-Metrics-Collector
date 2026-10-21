"""Unit tests for Teleserver Pulse metrics collection."""

from __future__ import annotations

import json
import unittest

from teleserver_pulse.metrics import (
    _container_cpu_percent,
    _container_memory,
    collect_all,
    collect_containers,
    collect_system_metrics,
    human_bytes,
)


class SystemMetricsTests(unittest.TestCase):
    def test_collect_system_metrics_shape(self) -> None:
        metrics = collect_system_metrics(sample_interval=0.0)
        self.assertGreaterEqual(metrics.cpu_percent, 0.0)
        self.assertLessEqual(metrics.cpu_percent, 100.0)
        self.assertGreater(metrics.memory_total_bytes, 0)
        self.assertGreaterEqual(metrics.memory_percent, 0.0)
        self.assertLessEqual(metrics.memory_percent, 100.0)
        self.assertGreaterEqual(metrics.uptime_seconds, 0)
        self.assertGreaterEqual(len(metrics.disks), 1)

    def test_to_dict_is_json_serialisable(self) -> None:
        metrics = collect_system_metrics(sample_interval=0.0)
        payload = metrics.to_dict()
        text = json.dumps(payload)
        self.assertIn('"cpu_percent"', text)
        self.assertIn('"disks"', text)

    def test_collect_all_without_containers(self) -> None:
        result = collect_all(include_containers=False)
        self.assertEqual(result.containers, [])
        self.assertIsNotNone(result.docker_error)


class DockerParsingTests(unittest.TestCase):
    def test_cpu_percent_from_stats(self) -> None:
        stats = {
            "cpu_stats": {
                "cpu_usage": {"total_usage": 2_000_000},
                "system_cpu_usage": 10_000_000,
                "online_cpus": 2,
            },
            "precpu_stats": {
                "cpu_usage": {"total_usage": 1_000_000},
                "system_cpu_usage": 9_000_000,
            },
        }
        # (1_000_000 / 1_000_000) * 2 * 100 = 200
        self.assertEqual(_container_cpu_percent(stats), 200.0)

    def test_cpu_percent_missing_stats(self) -> None:
        self.assertEqual(_container_cpu_percent({}), 0.0)

    def test_memory_zero_limit(self) -> None:
        self.assertEqual(_container_memory({}), (0, 0, 0.0))

    def test_collect_containers_never_raises(self) -> None:
        containers, error = collect_containers()
        self.assertIsInstance(containers, list)
        self.assertTrue(error is None or isinstance(error, str))


class FormattingTests(unittest.TestCase):
    def test_human_bytes(self) -> None:
        self.assertEqual(human_bytes(512), "512 B")
        self.assertEqual(human_bytes(1536), "1.5 KiB")
        self.assertEqual(human_bytes(2 * 1024 * 1024), "2.0 MiB")


if __name__ == "__main__":
    unittest.main()
