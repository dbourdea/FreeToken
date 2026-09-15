"""The engine's own process-tree footprint, never system-wide host telemetry.

RAM is summed Linux PSS. VRAM is per-process GPU memory from NVML/``nvidia-smi`` or
``amd-smi``. Byte fields remain integers for API compatibility; availability fields prevent an
unavailable best-effort probe from being misrepresented as a measured zero.
"""

from __future__ import annotations

import json
import subprocess
import threading
import time
from typing import Callable

from . import osproc


def engine_footprint(pid: int | None) -> dict:
    if pid is None:
        return {
            "ramBytes": 0, "vramBytes": 0, "pids": [],
            "ramAvailable": False, "vramAvailable": False,
            "ramSource": None, "vramSource": None,
        }
    pids = osproc.tree_pids(pid)
    ram_parts = [osproc.read_pss_bytes_if_available(p) for p in pids]
    ram_available = bool(ram_parts) and all(value is not None for value in ram_parts)
    ram = sum(value or 0 for value in ram_parts)
    vram, vram_available, vram_source = _vram_measurement_for_pids(pids)
    return {
        "ramBytes": ram,
        "vramBytes": vram,
        "pids": pids,
        "ramAvailable": ram_available,
        "vramAvailable": vram_available,
        "ramSource": "proc-smaps-rollup-pss" if ram_available else None,
        "vramSource": vram_source,
    }


class FootprintCache:
    """Single-flight + short-TTL cache over ``engine_footprint``. Clients poll metrics frequently
    and an NVML/nvidia-smi probe can take seconds on a busy GPU; without this, every poll pays
    that cost and can back up the proxy executor. Concurrent callers within the TTL collapse to
    one probe."""

    def __init__(self, *, ttl_s: float = 2.0, now: Callable[[], float] = time.monotonic) -> None:
        self._ttl = ttl_s
        self._now = now
        self._lock = threading.Lock()
        self._cache: dict[int | None, tuple[float, dict]] = {}

    def get(self, pid: int | None) -> dict:
        with self._lock:
            hit = self._cache.get(pid)
            if hit is not None and (self._now() - hit[0]) < self._ttl:
                return hit[1]
            val = engine_footprint(pid)
            self._cache[pid] = (self._now(), val)
            return val


def vram_bytes_for_pids(pids: list[int]) -> int:
    return _vram_measurement_for_pids(pids)[0]


def _vram_measurement_for_pids(pids: list[int]) -> tuple[int, bool, str | None]:
    want = set(pids)
    if not want:
        return 0, False, None
    available_source = None
    for source, probe in (
        ("nvml", _nvml_process_vram),
        ("nvidia-smi", _smi_process_vram),
        ("amd-smi", _amd_smi_process_vram),
    ):
        usage = probe()
        if usage is not None:
            if any(pid in usage for pid in want):
                return sum(nbytes for p, nbytes in usage.items() if p in want), True, source
            available_source = available_source or source
    if available_source is not None:
        return 0, True, available_source
    return 0, False, None


# NVML is initialized ONCE and held for the daemon's life — nvmlInit()+nvmlShutdown() on every
# call costs seconds on a busy GPU. None = not yet tried, True = ready, False = unavailable.
_NVML = {"ready": None}
_NVML_LOCK = threading.Lock()


def _nvml_ready():
    with _NVML_LOCK:
        if _NVML["ready"] is None:
            try:
                import pynvml  # optional; not a hard dep

                pynvml.nvmlInit()
                _NVML["ready"] = pynvml
            except Exception:  # noqa: BLE001
                _NVML["ready"] = False
        return _NVML["ready"]


def _nvml_process_vram() -> dict[int, int] | None:
    pynvml = _nvml_ready()
    if not pynvml:
        return None
    out: dict[int, int] = {}
    queried = False
    try:
        count = pynvml.nvmlDeviceGetCount()
        for i in range(count):
            handle = pynvml.nvmlDeviceGetHandleByIndex(i)
            for getter in (
                getattr(pynvml, "nvmlDeviceGetComputeRunningProcesses_v3", None),
                getattr(pynvml, "nvmlDeviceGetComputeRunningProcesses", None),
            ):
                if getter is None:
                    continue
                try:
                    for proc in getter(handle):
                        used = getattr(proc, "usedGpuMemory", None)
                        if used:  # None == "not available", per NVML
                            out[int(proc.pid)] = out.get(int(proc.pid), 0) + int(used)
                    queried = True
                    break
                except Exception:  # noqa: BLE001
                    continue
    except Exception:  # noqa: BLE001
        return out or None
    # A successfully queried empty process list is a real zero. If every getter failed,
    # ``queried`` stays false and the command-line fallbacks still run.
    return out if queried else None


def _smi_process_vram() -> dict[int, int] | None:
    try:
        out = subprocess.run(
            [
                "nvidia-smi",
                "--query-compute-apps=pid,used_memory",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=3.0,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if out.returncode != 0:
        return None
    usage: dict[int, int] = {}
    malformed = False
    for line in out.stdout.splitlines():
        parts = [p.strip() for p in line.split(",")]
        if len(parts) != 2 or not parts[0].isdigit() or not parts[1].isdigit():
            if line.strip():
                malformed = True
            continue
        usage[int(parts[0])] = usage.get(int(parts[0]), 0) + int(parts[1]) * 1024 * 1024  # MiB
    return None if malformed else usage


def _memory_bytes(value) -> int | None:
    """Parse AMD SMI's version-dependent JSON scalar or ``{value, unit}`` form."""
    if isinstance(value, dict) and "value" in value:
        unit = value.get("unit", "B")
        value = value["value"]
    elif isinstance(value, str):
        parts = value.strip().split()
        if not parts:
            return None
        value, unit = parts[0], parts[1] if len(parts) > 1 else "B"
    else:
        unit = "B"
    if isinstance(value, bool):
        return None
    try:
        amount = float(value)
    except (TypeError, ValueError):
        return None
    scales = {
        "b": 1, "kb": 1000, "mb": 1000**2, "gb": 1000**3, "tb": 1000**4,
        "kib": 1024, "mib": 1024**2, "gib": 1024**3, "tib": 1024**4,
    }
    scale = scales.get(str(unit).strip().lower())
    if scale is None or amount < 0:
        return None
    return int(amount * scale)


def _amd_smi_process_vram() -> dict[int, int] | None:
    """Read process VRAM from the documented ``amd-smi process --json`` schema."""
    try:
        out = subprocess.run(
            ["amd-smi", "process", "--json", "--general"],
            capture_output=True,
            text=True,
            timeout=3.0,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if out.returncode != 0:
        return None
    try:
        doc = json.loads(out.stdout)
    except (json.JSONDecodeError, TypeError):
        return None

    usage: dict[int, int] = {}
    saw_process = False
    saw_vram = False

    def visit(node) -> None:
        nonlocal saw_process, saw_vram
        if isinstance(node, dict):
            fields = {str(key).lower(): value for key, value in node.items()}
            pid = fields.get("pid")
            memory = fields.get("memory_usage")
            if isinstance(pid, int) and not isinstance(pid, bool):
                saw_process = True
                if isinstance(memory, dict):
                    memory_fields = {str(key).lower(): value for key, value in memory.items()}
                    vram = _memory_bytes(memory_fields.get("vram_mem"))
                    if vram is not None:
                        saw_vram = True
                        usage[pid] = usage.get(pid, 0) + vram
            for child in node.values():
                visit(child)
        elif isinstance(node, list):
            for child in node:
                visit(child)

    visit(doc)
    return None if saw_process and not saw_vram else usage
