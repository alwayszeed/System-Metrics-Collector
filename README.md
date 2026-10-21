# System Metrics Collector

> Bagian dari seri **Teleserver Pulse** — **Day 5** (fondasi kolektor metrik).

Kolektor metrik berbasis Python yang membaca **CPU, RAM, disk, uptime, dan daftar kontainer Docker** menggunakan [`psutil`](https://pypi.org/project/psutil/) dan [Docker SDK for Python](https://docker-py.readthedocs.io/).

## Fitur

- Metrik CPU (persentase, core, load average), memory, swap, uptime.
- Disk usage untuk root filesystem (dan semua mountpoint di Linux/macOS).
- Daftar kontainer Docker: nama, image, state, CPU %, memory usage/limit/percent.
- Docker bersifat opsional — jika daemon/SDK tidak ada, kolektor tetap jalan dan melaporkan `docker_error` tanpa crash.
- Output JSON (untuk konsumsi bot/alerting) atau human-readable.
- Unit test dengan `unittest`.

## Struktur

```
teleserver_pulse/
  metrics.py     # psutil + Docker SDK collection
  models.py      # dataclass untuk SystemMetrics, DiskMetrics, ContainerMetrics
  cli.py         # argparse CLI (--json, --no-docker, --disk)
tests/
  test_metrics.py
```

## Instalasi

```bash
pip install -r requirements.txt
```

Docker SDK membutuhkan akses ke Docker daemon (`/var/run/docker.sock` di Linux/macOS atau Docker Desktop di Windows).

## Pemakaian

```bash
# Tampilan manusiawi
python -m teleserver_pulse

# JSON untuk integrasi
python -m teleserver_pulse --json

# Lewati Docker (host tanpa kontainer)
python -m teleserver_pulse --no-docker
```

Contoh output JSON:

```json
{
  "system": {
    "cpu_percent": 12.4,
    "memory_percent": 48.1,
    "disks": [{ "path": "/", "percent": 62.0 }]
  },
  "containers": [
    { "name": "nginx", "state": "running", "cpu_percent": 0.3, "memory_percent": 1.2 }
  ],
  "docker_error": null
}
```

## Sebagai library

```python
from teleserver_pulse import collect_all

result = collect_all()
print(result.system.cpu_percent)
for container in result.containers:
    print(container.name, container.state)
```

## Test

```bash
python -m unittest discover -s tests -v
```

## Seri Teleserver Pulse

| Hari | Fokus | Repo |
|------|-------|------|
| Day 5 | System metrics collector (psutil + Docker SDK) | **repo ini** |
| Day 6 | Telegram bot: inline keyboard, restart, auth | [Telegram Bot Interactive Handler](https://github.com/alwayszeed/Telegram-Bot-Interactive-Handler) |
| Day 7 | Auto-alerting >85% + time-series logger | [Auto-Alerting & Time-Series Logger](https://github.com/alwayszeed/Auto-Alerting-Time-Series-Logger) |
