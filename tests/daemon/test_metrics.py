import json
from types import SimpleNamespace

from freetoken.daemon import metrics


def test_amd_smi_process_vram_parses_multi_gpu_json(monkeypatch):
    doc = [
        {"gpu": 0, "process_list": [{"process_info": {
            "pid": 41,
            "memory_usage": {"vram_mem": {"value": 2, "unit": "GiB"}},
        }}]},
        {"gpu": 1, "process_list": [{"process_info": {
            "pid": 41,
            "memory_usage": {"vram_mem": {"value": 512, "unit": "MiB"}},
        }}, {"process_info": {
            "pid": 42,
            "memory_usage": {"vram_mem": "1.5 GB"},
        }}]},
    ]
    monkeypatch.setattr(metrics.subprocess, "run", lambda *args, **kwargs: SimpleNamespace(
        returncode=0, stdout=json.dumps(doc)
    ))

    assert metrics._amd_smi_process_vram() == {
        41: 2 * 1024**3 + 512 * 1024**2,
        42: 1_500_000_000,
    }


def test_amd_smi_process_vram_distinguishes_empty_from_unavailable(monkeypatch):
    monkeypatch.setattr(metrics.subprocess, "run", lambda *args, **kwargs: SimpleNamespace(
        returncode=0, stdout="[]"
    ))
    assert metrics._amd_smi_process_vram() == {}

    monkeypatch.setattr(metrics.subprocess, "run", lambda *args, **kwargs: SimpleNamespace(
        returncode=1, stdout=""
    ))
    assert metrics._amd_smi_process_vram() is None

    monkeypatch.setattr(metrics.subprocess, "run", lambda *args, **kwargs: SimpleNamespace(
        returncode=0, stdout='[{"process_info":{"pid":41,"memory_usage":{}}}]'
    ))
    assert metrics._amd_smi_process_vram() is None


def test_vram_measurement_falls_through_to_amd_smi(monkeypatch):
    monkeypatch.setattr(metrics, "_nvml_process_vram", lambda: None)
    monkeypatch.setattr(metrics, "_smi_process_vram", lambda: {})
    monkeypatch.setattr(metrics, "_amd_smi_process_vram", lambda: {41: 123, 42: 456})

    assert metrics._vram_measurement_for_pids([41]) == (123, True, "amd-smi")


def test_engine_footprint_reports_sources_and_availability(monkeypatch):
    monkeypatch.setattr(metrics.osproc, "tree_pids", lambda pid: [pid, pid + 1])
    monkeypatch.setattr(metrics.osproc, "read_pss_bytes_if_available", lambda pid: pid * 10)
    monkeypatch.setattr(
        metrics, "_vram_measurement_for_pids", lambda pids: (1234, True, "amd-smi")
    )

    assert metrics.engine_footprint(10) == {
        "ramBytes": 210,
        "vramBytes": 1234,
        "pids": [10, 11],
        "ramAvailable": True,
        "vramAvailable": True,
        "ramSource": "proc-smaps-rollup-pss",
        "vramSource": "amd-smi",
    }


def test_engine_footprint_does_not_label_fallback_zero_as_measured(monkeypatch):
    monkeypatch.setattr(metrics.osproc, "tree_pids", lambda pid: [pid])
    monkeypatch.setattr(metrics.osproc, "read_pss_bytes_if_available", lambda pid: None)
    monkeypatch.setattr(metrics, "_vram_measurement_for_pids", lambda pids: (0, False, None))

    footprint = metrics.engine_footprint(10)
    assert footprint["ramBytes"] == footprint["vramBytes"] == 0
    assert footprint["ramAvailable"] is footprint["vramAvailable"] is False
    assert footprint["ramSource"] is footprint["vramSource"] is None
