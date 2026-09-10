from __future__ import annotations

import pytest
from concurrent.futures import ThreadPoolExecutor
from fastapi.testclient import TestClient

from freetoken.daemon.catalog import CatalogError, ModelCatalog
from freetoken.daemon.app import build_app
from freetoken.daemon import client as daemon_client
from freetoken.daemon.logring import LogRing
from freetoken.daemon.readiness import wait_for_ready


def test_catalog_reads_named_profiles_without_shell_interpolation(tmp_path):
    path = tmp_path / "models.toml"
    path.write_text(
        """[models.qwen-coder]\nmodel = \"/models/qwen.gguf\"\nport = 1922\nargs = [\"--max-seq-len-override\", \"32768\"]\ndescription = \"coding profile\"\n""",
        encoding="utf-8",
    )
    catalog = ModelCatalog.load(str(path))
    assert catalog.get("qwen-coder").request() == {
        "model": "/models/qwen.gguf", "port": 1922, "args": ["--max-seq-len-override", "32768"]
    }
    assert catalog.public() == [{
        "name": "qwen-coder", "model": "/models/qwen.gguf", "port": 1922,
        "args": ["--max-seq-len-override", "32768"], "description": "coding profile", "readyTimeoutS": 120.0,
    }]


@pytest.mark.parametrize("content, message", [
    ("[models.bad]\nmodel = 'm'\nargs = ['--port', '9']\n", "must not set --model or --port"),
    ("[models.bad]\nmodel = 'm'\ncmd = 'anything'\n", "unsupported keys"),
    ("[models.bad]\nmodel = ''\n", "non-empty string"),
    ("[models.bad]\nmodel = 'm'\nport = 0\n", "1 through 65535"),
])
def test_catalog_rejects_ambiguous_or_shell_style_profiles(tmp_path, content, message):
    path = tmp_path / "models.toml"
    path.write_text(content, encoding="utf-8")
    with pytest.raises(CatalogError, match=message):
        ModelCatalog.load(str(path))


def test_catalog_unknown_profile_has_operator_facing_error():
    with pytest.raises(CatalogError, match="unknown model profile 'missing'"):
        ModelCatalog.empty().get("missing")


def test_readiness_waits_for_engine_health_not_just_a_listening_process():
    class Manager:
        def status(self):
            return {"running": True, "pid": 44}

    class Probe:
        def __init__(self):
            self.docs = iter([
                {"reachable": True, "status": "loading"},
                {"reachable": True, "status": "ok", "model": "m"},
            ])

        def fresh_health(self, port):
            assert port == 1922
            return next(self.docs)

    clock = iter([0.0, 0.0, 0.1, 0.1])
    result = wait_for_ready(Manager(), Probe(), pid=44, port=1922, timeout_s=1, now=lambda: next(clock), sleep=lambda _: None)
    assert result == {"ready": True, "health": {"reachable": True, "status": "ok", "model": "m"}}


def test_readiness_timeout_leaves_the_existing_engine_under_manager_control():
    class Manager:
        def status(self):
            return {"running": True, "pid": 44}

    class Probe:
        def fresh_health(self, port):
            return {"reachable": True, "status": "loading"}

    clock = iter([0.0, 0.0, 1.0])
    result = wait_for_ready(Manager(), Probe(), pid=44, port=1922, timeout_s=1, now=lambda: next(clock), sleep=lambda _: None)
    assert result == {
        "ready": False,
        "reason": "timeout",
        "health": {"reachable": True, "status": "loading"},
    }


def test_profile_api_uses_validated_catalog_and_existing_switch_transaction(tmp_path):
    path = tmp_path / "models.toml"
    path.write_text("[models.coding]\nmodel = '/models/coding.gguf'\nport = 1922\nargs = ['--max-seq-len-override', '32768']\n", encoding="utf-8")

    class Manager:
        def __init__(self):
            self.calls = []
            self.running = False

        def status(self):
            return {"running": self.running, "pid": 101 if self.running else None, "port": 1922 if self.running else None}

        def start(self, model, port, args):
            self.calls.append(("start", model, port, args))
            self.running = True
            return {"started": True, "model": model, "port": port}

        def switch(self, model, port, args, force):
            self.calls.append(("switch", model, port, args, force))
            self.running = True
            return {"switched": True, "model": model, "port": port}

        def switch_for_readiness(self, *args):
            return self.switch(*args), None

    class Probe:
        def fresh_health(self, port):
            return {"reachable": True, "status": "ok", "port": port}

    manager = Manager()
    with ThreadPoolExecutor(1) as lifecycle, ThreadPoolExecutor(1) as proxy:
        app = build_app(
            manager=manager, ring=LogRing(), probe=Probe(), footprint_fn=lambda pid: {},
            lifecycle_pool=lifecycle, proxy_pool=proxy, catalog=ModelCatalog.load(str(path)), token="secret",
        )
        client = TestClient(app)
        assert client.get("/models").status_code == 401
        listing = client.get("/models", headers={"X-FT-Token": "secret"})
        assert listing.status_code == 200
        assert listing.json()["data"][0]["name"] == "coding"
        started = client.post("/engine/start-profile", json={"name": "coding"}, headers={"X-FT-Token": "secret"})
        assert started.status_code == 200
        assert started.json()["profile"] == "coding"
        assert started.json()["readiness"]["ready"] is True
        switched = client.post("/engine/switch-profile", json={"name": "coding", "force": True}, headers={"X-FT-Token": "secret"})
        assert switched.status_code == 200
    assert manager.calls == [
        ("start", "/models/coding.gguf", 1922, ["--max-seq-len-override", "32768"]),
        ("switch", "/models/coding.gguf", 1922, ["--max-seq-len-override", "32768"], True),
    ]


def test_client_shutdown_uses_the_daemon_shutdown_transaction(monkeypatch, capsys):
    seen = {}

    def request(method, url, path, **kwargs):
        seen.update(method=method, url=url, path=path, **kwargs)
        return {"stopping": True}

    monkeypatch.setattr(daemon_client, "_request_json", request)
    assert daemon_client.main(["shutdown", "--url", "http://daemon:1900", "--force"]) == 0
    assert seen == {
        "method": "POST", "url": "http://daemon:1900", "path": "/shutdown",
        "body": {"force": True}, "token": None, "timeout": daemon_client.DEFAULT_LIFECYCLE_TIMEOUT,
    }
    assert '"stopping": true' in capsys.readouterr().out


def test_router_policy_is_strict_and_public_model_fields_are_safe(tmp_path):
    path = tmp_path / "models.toml"
    path.write_text("""
[router]
api_keys = ["one", "two"]
default_ttl_s = 300
unload_timeout_s = 45
upstream_timeout_s = 42
scheduler = "fifo"

[router.groups.interactive]
members = ["coding", "chat"]
swap = true
exclusive = true

[models.coding]
model = "coding.gguf"
ttl_s = 0
unload_timeout_s = 60
priority = 10
group = "interactive"

[models.chat]
model = "chat.gguf"
priority = -5
""", encoding="utf-8")
    catalog = ModelCatalog.load(str(path))
    assert catalog.settings.api_keys == ("one", "two")
    assert catalog.settings.default_ttl_s == 300
    assert catalog.settings.upstream_timeout_s == 42
    assert catalog.settings.groups[0].members == ("coding", "chat")
    public = {item["name"]: item for item in catalog.public()}
    assert public["coding"] == {
        "name": "coding", "model": "coding.gguf", "args": [], "readyTimeoutS": 120.0,
        "ttlS": 0.0, "unloadTimeoutS": 60.0, "priority": 10, "group": "interactive",
    }
    assert "api_keys" not in str(public)


@pytest.mark.parametrize("router, message", [
    ("[router]\nscheduler = 'lifo'", "scheduler"),
    ("[router]\nupstream_timeout_s = 0", "upstream_timeout_s"),
    ("[router]\napi_keys = ['same', 'same']", "duplicates"),
    ("[router.groups.g]\nmembers = ['missing']", "configured models"),
    ("[router.groups.g]\nmembers = ['a']\npersistent = true", "persistent"),
    ("group = 'other'", "must match"),
])
def test_router_policy_rejects_ambiguous_or_unsafe_configuration(tmp_path, router, message):
    path = tmp_path / "models.toml"
    path.write_text("[models.a]\nmodel = 'a.gguf'\n" + router, encoding="utf-8")
    with pytest.raises(CatalogError, match=message):
        ModelCatalog.load(str(path))
