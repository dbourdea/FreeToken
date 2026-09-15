"""The engine's own process-tree footprint, never system-wide host telemetry.

RAM is summed Linux PSS. VRAM is per-process GPU memory from NVML/``nvidia-smi`` or
``amd-smi``. Byte fields remain integers for API compatibility; availability fields prevent an
unavailable best-effort probe from being misrepresented as a measured zero.
"""
# What: document the engine s own process tree footprint in the metrics docstring; why: introspection and maintainers read this exact docstring fragment to understand metrics behavior without executing it.
# What: document ram is summed linux pss vram in the metrics docstring; why: introspection and maintainers read this exact docstring fragment to understand metrics behavior without executing it.
# What: document amd smi byte fields remain integers for in the metrics docstring; why: introspection and maintainers read this exact docstring fragment to understand metrics behavior without executing it.
# What: document unavailable best effort probe from being misrepresented in the metrics docstring; why: introspection and maintainers read this exact docstring fragment to understand metrics behavior without executing it.
# What: preserve the paragraph boundary in the the metrics docstring; why: introspection and maintainers read this paragraph break to understand metrics behavior without executing it.

from __future__ import annotations

# What: import json for amd smi process vram using json; why: _amd_smi_process_vram uses json loads, making that imported dependency available to its named operation.
import json
import subprocess
import threading
import time
from typing import Callable

from . import osproc


def engine_footprint(pid: int | None) -> dict:
    if pid is None:
        # What: return ram bytes and vram bytes and pids and ram available and vram available from engine_footprint; why: engine_footprint exposes ram bytes and vram bytes and pids and ram available and vram available so its caller can continue with the function\'s computed outcome.
        return {
            # What: map the ram bytes field as 0; why: engine_footprint carries ram bytes into "ramBytes": 0, "vramBytes": 0, "pids": [].
            "ramBytes": 0, "vramBytes": 0, "pids": [],
            # What: map the ram available field as false; why: engine_footprint carries ram available into "ramAvailable": False, "vramAvailable": False.
            "ramAvailable": False, "vramAvailable": False,
            # What: map the ram source field as the fixture input; why: engine_footprint carries ram source into "ramSource": None, "vramSource": None.
            "ramSource": None, "vramSource": None,
        # What: complete the enclosing predicate mapping with ram bytes and vram bytes and pids and ram available and vram available; why: engine_footprint groups the supplied clauses as one enclosing predicate mapping mapping before its value is consumed.
        }
    pids = osproc.tree_pids(pid)
    # What: compute ram parts from read pss bytes if available and p and pids and osproc; why: ram available bool ram parts and all value later reads ram parts, so engine_footprint must retain the computed value under that name.
    ram_parts = [osproc.read_pss_bytes_if_available(p) for p in pids]
    # What: compute ram available from bool and ram parts and all and value; why: ram available ram available later reads ram available, so engine_footprint must retain the computed value under that name.
    ram_available = bool(ram_parts) and all(value is not None for value in ram_parts)
    # What: compute ram from sum and value and ram parts and 0; why: ram bytes ram later reads ram, so engine_footprint must retain the computed value under that name.
    ram = sum(value or 0 for value in ram_parts)
    # What: compute vram and vram available and vram source from vram measurement for pids and pids; why: vram bytes vram later reads vram and vram available and vram source, so engine_footprint must retain the computed value under that name.
    vram, vram_available, vram_source = _vram_measurement_for_pids(pids)
    # What: return ram and vram and pids and ram available from engine_footprint; why: engine_footprint exposes ram and vram and pids and ram available so its caller can continue with the function\'s computed outcome.
    return {
        # What: map the ram bytes field as ram; why: engine_footprint carries ram bytes into "ramBytes": ram.
        "ramBytes": ram,
        # What: map the vram bytes field as vram; why: engine_footprint carries vram bytes into "vramBytes": vram.
        "vramBytes": vram,
        # What: map the pids field as pids; why: engine_footprint carries pids into "pids": pids.
        "pids": pids,
        # What: map the ram available field as ram available; why: engine_footprint carries ram available into "ramAvailable": ram_available.
        "ramAvailable": ram_available,
        # What: map the vram available field as vram available; why: engine_footprint carries vram available into "vramAvailable": vram_available.
        "vramAvailable": vram_available,
        # What: map the ram source field as ram available and proc smaps rollup pss; why: engine_footprint carries ram source into "ramSource": "proc-smaps-rollup-pss" if ram_available else None.
        "ramSource": "proc-smaps-rollup-pss" if ram_available else None,
        # What: map the vram source field as vram source; why: engine_footprint carries vram source into "vramSource": vram_source.
        "vramSource": vram_source,
    # What: complete the enclosing predicate mapping with ram bytes and vram bytes and pids and ram available and vram available; why: engine_footprint groups the supplied clauses as one enclosing predicate mapping mapping before its value is consumed.
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
    # What: return vram measurement for pids and pids and 0 from vram_bytes_for_pids; why: vram_bytes_for_pids exposes vram measurement for pids and pids and 0 so its caller can continue with the function\'s computed outcome.
    return _vram_measurement_for_pids(pids)[0]


# What: define _vram_measurement_for_pids around pids; why: its direct callers call _vram_measurement_for_pids for vram measurement for pids and rely on this exact input and result contract.
def _vram_measurement_for_pids(pids: list[int]) -> tuple[int, bool, str | None]:
    want = set(pids)
    if not want:
        # What: return 0 and false from _vram_measurement_for_pids; why: _vram_measurement_for_pids exposes 0 and false so its caller can continue with the function\'s computed outcome.
        return 0, False, None
    # What: compute available source from the named fixture input; why: available source available source or source later reads available source, so _vram_measurement_for_pids must retain the computed value under that name.
    available_source = None
    # What: iterate across nvml process vram and smi process vram and amd smi process vram to perform usage and probe; why: _vram_measurement_for_pids repeats the body only while or for the loop header admits an iteration.
    for source, probe in (
        # What: apply the nvml nvml process vram portion of the enclosing predicate; why: this clause remains in _vram_measurement_for_pids\'s enclosing expression so its grouping and evaluation order stay intact.
        ("nvml", _nvml_process_vram),
        # What: apply the nvidia smi smi process vram portion of the enclosing predicate; why: this clause remains in _vram_measurement_for_pids\'s enclosing expression so its grouping and evaluation order stay intact.
        ("nvidia-smi", _smi_process_vram),
        # What: apply the amd smi amd smi process vram portion of the enclosing predicate; why: this clause remains in _vram_measurement_for_pids\'s enclosing expression so its grouping and evaluation order stay intact.
        ("amd-smi", _amd_smi_process_vram),
    # What: complete the enclosing predicate collection with nvml process vram and nvml and smi process vram and nvidia smi and amd smi process vram and amd smi; why: _vram_measurement_for_pids groups the supplied clauses as one enclosing predicate collection collection before its value is consumed.
    ):
        # What: compute usage from probe; why: if usage is not later reads usage, so _vram_measurement_for_pids must retain the computed value under that name.
        usage = probe()
        # What: gate on usage before any and source and pid and usage and want; why: _vram_measurement_for_pids admits any and source and pid and usage and want only for this predicate and excludes the opposite state.
        if usage is not None:
            # What: gate on any and pid and usage and want before source and sum and nbytes and p and items; why: _vram_measurement_for_pids admits source and sum and nbytes and p and items only for this predicate and excludes the opposite state.
            if any(pid in usage for pid in want):
                # What: return source and sum and nbytes and p from _vram_measurement_for_pids; why: _vram_measurement_for_pids exposes source and sum and nbytes and p so its caller can continue with the function\'s computed outcome.
                return sum(nbytes for p, nbytes in usage.items() if p in want), True, source
            # What: compute available source from available source and source; why: if available source is not later reads available source, so _vram_measurement_for_pids must retain the computed value under that name.
            available_source = available_source or source
    # What: gate on available source before available source; why: _vram_measurement_for_pids admits available source only for this predicate and excludes the opposite state.
    if available_source is not None:
        # What: return available source and 0 and true from _vram_measurement_for_pids; why: _vram_measurement_for_pids exposes available source and 0 and true so its caller can continue with the function\'s computed outcome.
        return 0, True, available_source
    # What: return 0 and false from _vram_measurement_for_pids; why: _vram_measurement_for_pids exposes 0 and false so its caller can continue with the function\'s computed outcome.
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
    # What: compute queried from false; why: queried later reads queried, so _nvml_process_vram must retain the computed value under that name.
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
                    # What: compute queried from true; why: return out if queried else later reads queried, so _nvml_process_vram must retain the computed value under that name.
                    queried = True
                    break
                except Exception:  # noqa: BLE001
                    continue
    except Exception:  # noqa: BLE001
        return out or None
    # A successfully queried empty process list is a real zero. If every getter failed,
    # ``queried`` stays false and the command-line fallbacks still run.
    # What: return queried and out from _nvml_process_vram; why: _nvml_process_vram exposes queried and out so its caller can continue with the function\'s computed outcome.
    return out if queried else None


# What: define _smi_process_vram around the current object state; why: its direct callers call _smi_process_vram for smi process vram and rely on this exact input and result contract.
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
        # What: return no value from _smi_process_vram; why: _smi_process_vram returns no value to callers that depend on its completed result.
        return None
    if out.returncode != 0:
        # What: return no value from _smi_process_vram; why: _smi_process_vram returns no value to callers that depend on its completed result.
        return None
    usage: dict[int, int] = {}
    # What: compute malformed from false; why: malformed later reads malformed, so _smi_process_vram must retain the computed value under that name.
    malformed = False
    for line in out.stdout.splitlines():
        parts = [p.strip() for p in line.split(",")]
        if len(parts) != 2 or not parts[0].isdigit() or not parts[1].isdigit():
            # What: gate on strip and line before malformed; why: _smi_process_vram admits malformed only for this predicate and excludes the opposite state.
            if line.strip():
                # What: compute malformed from true; why: return if malformed else usage later reads malformed, so _smi_process_vram must retain the computed value under that name.
                malformed = True
            continue
        usage[int(parts[0])] = usage.get(int(parts[0]), 0) + int(parts[1]) * 1024 * 1024  # MiB
    # What: return malformed and usage from _smi_process_vram; why: _smi_process_vram exposes malformed and usage so its caller can continue with the function\'s computed outcome.
    return None if malformed else usage


# What: define _memory_bytes around value; why: its direct callers call _memory_bytes for memory bytes and rely on this exact input and result contract.
def _memory_bytes(value) -> int | None:
    """Parse AMD SMI's version-dependent JSON scalar or ``{value, unit}`` form."""
    # What: document parse amd smi s version dependent json in the _memory_bytes docstring; why: introspection and maintainers read this exact docstring fragment to understand memory bytes behavior without executing it.
    # What: gate on isinstance and value and dict before unit and get and value; why: _memory_bytes admits unit and get and value only for this predicate and excludes the opposite state.
    if isinstance(value, dict) and "value" in value:
        # What: compute unit from get and value and unit and b; why: value unit parts parts if len later reads unit, so _memory_bytes must retain the computed value under that name.
        unit = value.get("unit", "B")
        # What: compute value from value and value; why: elif isinstance value str later reads value, so _memory_bytes must retain the computed value under that name.
        value = value["value"]
    # What: gate on isinstance and value and str before parts and split and strip and value; why: _memory_bytes admits parts and split and strip and value only for this predicate and excludes the opposite state.
    elif isinstance(value, str):
        # What: compute parts from split and strip and value; why: if not parts later reads parts, so _memory_bytes must retain the computed value under that name.
        parts = value.strip().split()
        # What: gate on parts before the computed value; why: _memory_bytes admits the computed value only for this predicate and excludes the opposite state.
        if not parts:
            # What: return no value from _memory_bytes; why: _memory_bytes returns no value to callers that depend on its completed result.
            return None
        # What: compute value and unit from parts and len and 0 and b and 1; why: if isinstance value bool later reads value and unit, so _memory_bytes must retain the computed value under that name.
        value, unit = parts[0], parts[1] if len(parts) > 1 else "B"
    # What: select the remaining branch that performs unit b; why: _memory_bytes covers the state excluded by the preceding predicate without conflating the two outcomes.
    else:
        # What: compute unit from b; why: scale scales get str unit strip lower later reads unit, so _memory_bytes must retain the computed value under that name.
        unit = "B"
    # What: gate on isinstance and value and bool before the computed value; why: _memory_bytes admits the computed value only for this predicate and excludes the opposite state.
    if isinstance(value, bool):
        # What: return no value from _memory_bytes; why: _memory_bytes returns no value to callers that depend on its completed result.
        return None
    # What: establish the handler boundary for the protected operation; why: _memory_bytes routes failures to type error and value error while preserving cleanup and success flow.
    try:
        # What: compute amount from float and value; why: if scale is or amount later reads amount, so _memory_bytes must retain the computed value under that name.
        amount = float(value)
    # What: handle type error and value error by return; why: _memory_bytes converts that failure into this concrete recovery, response, or cleanup behavior.
    except (TypeError, ValueError):
        # What: return no value from _memory_bytes; why: _memory_bytes returns no value to callers that depend on its completed result.
        return None
    # What: compute scales from b and kb and mb and gb and tb; why: scale scales get str unit strip lower later reads scales, so _memory_bytes must retain the computed value under that name.
    scales = {
        # What: map the b field as 1; why: _memory_bytes carries b through scales into scale scales get str unit strip lower.
        "b": 1, "kb": 1000, "mb": 1000**2, "gb": 1000**3, "tb": 1000**4,
        # What: map the kib field as 1024; why: _memory_bytes carries kib through scales into scale scales get str unit strip lower.
        "kib": 1024, "mib": 1024**2, "gib": 1024**3, "tib": 1024**4,
    # What: complete the scales mapping with b and kb and mb and gb and tb; why: _memory_bytes groups the supplied clauses as one scales mapping before its value is consumed.
    }
    # What: compute scale from get and scales and lower and strip; why: if scale is or amount later reads scale, so _memory_bytes must retain the computed value under that name.
    scale = scales.get(str(unit).strip().lower())
    # What: gate on scale and amount before the computed value; why: _memory_bytes admits the computed value only for this predicate and excludes the opposite state.
    if scale is None or amount < 0:
        # What: return no value from _memory_bytes; why: _memory_bytes returns no value to callers that depend on its completed result.
        return None
    # What: return int and amount and scale from _memory_bytes; why: _memory_bytes exposes int and amount and scale so its caller can continue with the function\'s computed outcome.
    return int(amount * scale)


# What: define _amd_smi_process_vram around the current object state; why: its direct callers call _amd_smi_process_vram for amd smi process vram and rely on this exact input and result contract.
def _amd_smi_process_vram() -> dict[int, int] | None:
    """Read process VRAM from the documented ``amd-smi process --json`` schema."""
    # What: document read process vram from the documented in the _amd_smi_process_vram docstring; why: introspection and maintainers read this exact docstring fragment to understand amd smi process vram behavior without executing it.
    # What: establish the handler boundary for the protected operation; why: _amd_smi_process_vram routes failures to oserror and subprocess error and subprocess while preserving cleanup and success flow.
    try:
        # What: compute out from run and subprocess and amd smi and process and json; why: if out returncode later reads out, so _amd_smi_process_vram must retain the computed value under that name.
        out = subprocess.run(
            # What: apply the amd smi process json general portion of out; why: _amd_smi_process_vram uses this clause to evaluate out as one grouped value.
            ["amd-smi", "process", "--json", "--general"],
            # What: supply capture output to subprocess.run; why: _amd_smi_process_vram binds this true value to subprocess.run's capture output input.
            capture_output=True,
            # What: supply text to subprocess.run; why: _amd_smi_process_vram binds this true value to subprocess.run's text input.
            text=True,
            # What: supply timeout to subprocess.run; why: _amd_smi_process_vram binds this 3 0 value to subprocess.run's timeout input.
            timeout=3.0,
        # What: complete the subprocess.run call with capture output and text and timeout; why: _amd_smi_process_vram groups the supplied clauses as one subprocess.run call before its value is consumed.
        )
    # What: handle oserror and subprocess error and subprocess by return; why: _amd_smi_process_vram converts that failure into this concrete recovery, response, or cleanup behavior.
    except (OSError, subprocess.SubprocessError):
        # What: return no value from _amd_smi_process_vram; why: _amd_smi_process_vram returns no value to callers that depend on its completed result.
        return None
    # What: gate on returncode and out before the computed value; why: _amd_smi_process_vram admits the computed value only for this predicate and excludes the opposite state.
    if out.returncode != 0:
        # What: return no value from _amd_smi_process_vram; why: _amd_smi_process_vram returns no value to callers that depend on its completed result.
        return None
    # What: establish the handler boundary for the protected operation; why: _amd_smi_process_vram routes failures to jsondecode error and type error and json while preserving cleanup and success flow.
    try:
        # What: compute doc from loads and stdout and json and out; why: visit doc later reads doc, so _amd_smi_process_vram must retain the computed value under that name.
        doc = json.loads(out.stdout)
    # What: handle jsondecode error and type error and json by return; why: _amd_smi_process_vram converts that failure into this concrete recovery, response, or cleanup behavior.
    except (json.JSONDecodeError, TypeError):
        # What: return no value from _amd_smi_process_vram; why: _amd_smi_process_vram returns no value to callers that depend on its completed result.
        return None

    # What: initialize usage as an empty runtime accumulator; why: _amd_smi_process_vram appends or maps entries into it during usage pid usage get pid 0 vram before consuming the aggregate.
    usage: dict[int, int] = {}
    # What: compute saw process from false; why: nonlocal saw process saw vram later reads saw process, so _amd_smi_process_vram must retain the computed value under that name.
    saw_process = False
    # What: compute saw vram from false; why: nonlocal saw process saw vram later reads saw vram, so _amd_smi_process_vram must retain the computed value under that name.
    saw_vram = False

    # What: define visit around node; why: its direct callers call visit for visit and rely on this exact input and result contract.
    def visit(node) -> None:
        # What: apply the nonlocal saw process saw vram portion of the enclosing predicate; why: this clause remains in visit\'s enclosing expression so its grouping and evaluation order stay intact.
        nonlocal saw_process, saw_vram
        # What: gate on isinstance and node and dict before fields and value and lower and key and items; why: visit admits fields and value and lower and key and items only for this predicate and excludes the opposite state.
        if isinstance(node, dict):
            # What: compute fields from value and lower and key and items; why: pid fields get pid later reads fields, so visit must retain the computed value under that name.
            fields = {str(key).lower(): value for key, value in node.items()}
            # What: compute pid from get and fields and pid; why: if isinstance pid int and not later reads pid, so visit must retain the computed value under that name.
            pid = fields.get("pid")
            # What: compute memory from get and fields and memory usage; why: if isinstance memory dict later reads memory, so visit must retain the computed value under that name.
            memory = fields.get("memory_usage")
            # What: gate on isinstance and pid and int and bool before saw process; why: visit admits saw process only for this predicate and excludes the opposite state.
            if isinstance(pid, int) and not isinstance(pid, bool):
                # What: compute saw process from true; why: the enclosing return or state update later reads saw process, so visit must retain the computed value under that name.
                saw_process = True
                # What: gate on isinstance and memory and dict before memory fields and value and lower and key and items; why: visit admits memory fields and value and lower and key and items only for this predicate and excludes the opposite state.
                if isinstance(memory, dict):
                    # What: compute memory fields from value and lower and key and items; why: vram memory bytes memory fields get vram mem later reads memory fields, so visit must retain the computed value under that name.
                    memory_fields = {str(key).lower(): value for key, value in memory.items()}
                    # What: compute vram from memory bytes and get and memory fields and vram mem; why: if vram is not later reads vram, so visit must retain the computed value under that name.
                    vram = _memory_bytes(memory_fields.get("vram_mem"))
                    # What: gate on vram before saw vram; why: visit admits saw vram only for this predicate and excludes the opposite state.
                    if vram is not None:
                        # What: compute saw vram from true; why: the enclosing return or state update later reads saw vram, so visit must retain the computed value under that name.
                        saw_vram = True
                        # What: compute usage entry from vram and get and pid and usage and 0; why: the enclosing return or state update later reads usage entry, so visit must retain the computed value under that name.
                        usage[pid] = usage.get(pid, 0) + vram
            # What: iterate across values and node to perform visit and child; why: visit repeats the body only while or for the loop header admits an iteration.
            for child in node.values():
                # What: call visit with child; why: visit invokes visit while performing elif isinstance node list; the call advances that operation through its result or side effect.
                visit(child)
        # What: gate on isinstance and node and list before child and node and visit; why: visit admits child and node and visit only for this predicate and excludes the opposite state.
        elif isinstance(node, list):
            # What: iterate across node to perform visit and child; why: visit repeats the body only while or for the loop header admits an iteration.
            for child in node:
                # What: call visit with child; why: visit invokes visit while performing the enclosing return; the call advances that operation through its result or side effect.
                visit(child)

    # What: call visit with doc; why: _amd_smi_process_vram invokes visit while performing return if saw process and not saw vram; the call advances that operation through its result or side effect.
    visit(doc)
    # What: return usage and saw process and saw vram from _amd_smi_process_vram; why: _amd_smi_process_vram exposes usage and saw process and saw vram so its caller can continue with the function\'s computed outcome.
    return None if saw_process and not saw_vram else usage
