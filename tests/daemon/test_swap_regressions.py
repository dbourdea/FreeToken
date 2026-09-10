"""Swap boundary regressions, runnable without the GPU runtime."""

import ast
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from freetoken.daemon.catalog import CatalogError, ModelCatalog
from freetoken.daemon import client as daemon_client
from freetoken.daemon.readiness import wait_for_ready
from freetoken.daemon.proxy import ServeProbe


@pytest.mark.parametrize("arg", ["--model-path", "--model-path=other", "--model-p", "--mod=other", "--por=8", "--"])
def test_catalog_rejects_owned_option_aliases(tmp_path, arg):
    path = tmp_path / "models.toml"
    path.write_text(f"[models.bad]\nmodel = 'm'\nargs = ['{arg}']\n", encoding="utf-8")
    with pytest.raises(CatalogError, match="must not set"):
        ModelCatalog.load(str(path))


def test_readiness_rechecks_generation_after_probe():
    class Manager:
        pid = 44

        def status(self):
            return {"running": True, "pid": self.pid}

    manager = Manager()

    class Probe:
        def fresh_health(self, port):
            manager.pid = 45
            return {"reachable": True, "status": "ok"}

    result = wait_for_ready(manager, Probe(), pid=44, port=1922, timeout_s=1)
    assert result["ready"] is False
    assert result["reason"] == "superseded"


def test_profile_client_reports_legacy_readiness_failure(monkeypatch):
    seen = {}

    def request(*args, **kwargs):
        seen.update(kwargs)
        return {"readiness": {"ready": False, "reason": "engine-error"}}

    monkeypatch.setattr(daemon_client, "_request_json", request)
    assert daemon_client.main(["start-profile", "coding"]) == 1
    assert seen["timeout"] == daemon_client.DEFAULT_PROFILE_TIMEOUT


def test_fresh_health_does_not_reuse_previous_model_cache():
    docs = iter([{"status": "ok", "instance_id": "old"}, {"status": "loading", "instance_id": "new"}])
    probe = ServeProbe(opener=lambda *_: next(docs), ttl_s=100)
    assert probe.health(1922)["status"] == "ok"
    assert probe.fresh_health(1922)["status"] == "loading"


@pytest.mark.parametrize("status,maintenance,expected", [
    ("loading", None, 503), ("error", None, 503),
    ("ok", "draining", 503), ("ok", "serving", 200),
])
def test_readiness_http_contract(status, maintenance, expected):
    # Execute the actual handlers, excluding unrelated torch-dependent metrics
    # imports. This is a CPU contract test, not a full serving integration test.
    source = Path(__file__).parents[2] / "python/freetoken/server/control_api.py"
    module = ast.parse(source.read_text(encoding="utf-8"))
    register = next(n for n in module.body if isinstance(n, ast.FunctionDef) and n.name == "register_control_routes")
    routes = [n for n in register.body if isinstance(n, ast.AsyncFunctionDef) and n.name in {"health", "ready"}]
    app = FastAPI()
    doc = {"status": status, "maintenance": maintenance}
    namespace = {"app": app, "build_health": lambda *_: doc, "get_state": lambda: None}
    exec(compile(ast.Module(body=routes, type_ignores=[]), str(source), "exec"), namespace)
    with TestClient(app) as client:
        assert client.get("/health").status_code == 200
        response = client.get("/ready")
        assert response.status_code == expected
        assert response.json() == doc
