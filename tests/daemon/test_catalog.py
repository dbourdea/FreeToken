from __future__ import annotations

import pytest
from concurrent.futures import ThreadPoolExecutor
from fastapi.testclient import TestClient

from freetoken.daemon.catalog import CatalogError, ModelCapabilities, ModelCatalog
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


def test_catalog_validates_custom_readiness_and_owned_loopback_proxy_targets(tmp_path):
    path = tmp_path / "models.toml"
    path.write_text(
        """[models.coding]
model = "coding.gguf"
port = 1922
check_endpoint = "/ready"
proxy = "http://127.0.0.1:${PORT}/gateway/v1"
""",
        encoding="utf-8",
    )

    profile = ModelCatalog.load(str(path)).get("coding")

    assert profile.check_endpoint == "/ready"
    assert profile.proxy_base_url(1922) == "http://127.0.0.1:1922/gateway/v1"
    assert profile.public()["checkEndpoint"] == "/ready"
    assert profile.public()["proxy"] == "http://127.0.0.1:${PORT}/gateway/v1"


@pytest.mark.parametrize("field,value,message", [
    ("check_endpoint", "ready", "absolute ASCII path"),
    ("check_endpoint", "/../health", "absolute ASCII path"),
    ("check_endpoint", "/health?token=x", "absolute ASCII path"),
    ("proxy", "http://127.0.0.1:1922", "127.0.0.1"),
    ("proxy", "http://localhost:${PORT}", "127.0.0.1"),
    ("proxy", "https://127.0.0.1:${PORT}", "127.0.0.1"),
    ("proxy", "http://127.0.0.1:${PORT}/../admin", "127.0.0.1"),
    ("proxy", "http://127.0.0.1:${PORT}/api?token=x", "127.0.0.1"),
])
def test_catalog_rejects_unsafe_readiness_or_proxy_targets(
    tmp_path, field, value, message
):
    path = tmp_path / "models.toml"
    path.write_text(
        f'[models.bad]\nmodel = "bad.gguf"\n{field} = "{value}"\n',
        encoding="utf-8",
    )
    with pytest.raises(CatalogError, match=message):
        ModelCatalog.load(str(path))


def test_catalog_validates_and_exposes_supported_listing_capabilities(tmp_path):
    path = tmp_path / "models.toml"
    path.write_text(
        """[models.coding]
model = "coding.gguf"

[models.coding.capabilities]
in = ["text"]
out = ["text"]
tools = true
context = 32768
""",
        encoding="utf-8",
    )

    profile = ModelCatalog.load(str(path)).get("coding")

    assert profile.capabilities == ModelCapabilities(("text",), ("text",), True, 32768)
    assert profile.public()["capabilities"] == {
        "in": ["text"], "out": ["text"], "tools": True, "context": 32768,
    }


def test_catalog_validates_request_fields_and_creates_variant_aliases(tmp_path):
    path = tmp_path / "models.toml"
    path.write_text(
        """[models.coding]
model = "coding.gguf"
drop_fields = ["metadata.private"]

[models.coding.set_fields]
temperature = 0.2
"max_tokens?" = 4096
"chat_template_kwargs.enable_thinking?" = true

[models.coding.set_fields_by_id."coding:high"]
temperature = 0.1
"chat_template_kwargs.reasoning_effort" = "high"
""",
        encoding="utf-8",
    )

    catalog = ModelCatalog.load(str(path))
    profile = catalog.get("coding:high")

    assert profile is catalog.get("coding")
    assert profile.aliases == ("coding:high",)
    assert profile.drop_fields == ("metadata.private",)
    assert profile.public()["setFields"] == {
        "temperature": 0.2,
        "chat_template_kwargs.enable_thinking?": True,
        "max_tokens?": 4096,
    }
    assert profile.public()["setFieldsById"] == {
        "coding:high": {
            "chat_template_kwargs.reasoning_effort": "high",
            "temperature": 0.1,
        }
    }


def test_catalog_hard_request_field_wins_over_soft_spelling(tmp_path):
    path = tmp_path / "models.toml"
    path.write_text(
        """[models.coding]
model = "coding.gguf"
[models.coding.set_fields]
max_tokens = 1000
"max_tokens?" = 2000
""",
        encoding="utf-8",
    )

    fields = ModelCatalog.load(str(path)).get("coding").set_fields

    assert [(field.key, field.value(), field.soft) for field in fields] == [
        ("max_tokens", 1000, False)
    ]


@pytest.mark.parametrize("declaration,message", [
    ('in = ["image"]', "unsupported modalities: image"),
    ('out = ["audio"]', "unsupported modalities: audio"),
    ('out = ["video"]', "unsupported modalities: video"),
    ('in = ["text", "text"]', "must not contain duplicates"),
    ("tools = 1", "tools must be a boolean"),
    ("context = -1", "context must be a nonnegative integer"),
    ("context = true", "context must be a nonnegative integer"),
    ("reranker = true", "unsupported keys: reranker"),
])
def test_catalog_rejects_unsupported_or_malformed_capabilities(
    tmp_path, declaration, message
):
    path = tmp_path / "models.toml"
    path.write_text(
        f'[models.coding]\nmodel = "coding.gguf"\n'
        f'[models.coding.capabilities]\n{declaration}\n',
        encoding="utf-8",
    )
    with pytest.raises(CatalogError, match=message):
        ModelCatalog.load(str(path))


@pytest.mark.parametrize("declaration,message", [
    ('[models.coding.set_fields]\nmodel = "other"', "must not set model"),
    ('[models.coding.set_fields]\n"model?" = "other"', "must not set model"),
    ('[models.coding.set_fields]\n"bad..path" = 1', "safe dot-delimited"),
    ('[models.coding.set_fields]\nstarted = 2026-09-14', "JSON-compatible"),
    (
        '[models.coding.set_fields_by_id."bad//alias"]\ntemperature = 1',
        "slash-separated",
    ),
])
def test_catalog_rejects_unsafe_request_field_configuration(
    tmp_path, declaration, message
):
    path = tmp_path / "models.toml"
    path.write_text(
        f'[models.coding]\nmodel = "coding.gguf"\n{declaration}\n',
        encoding="utf-8",
    )
    with pytest.raises(CatalogError, match=message):
        ModelCatalog.load(str(path))


def test_filter_generated_alias_cannot_collide_with_another_profile(tmp_path):
    path = tmp_path / "models.toml"
    path.write_text(
        """[models.one]
model = "one.gguf"
[models.one.set_fields_by_id.two]
temperature = 0.1
[models.two]
model = "two.gguf"
""",
        encoding="utf-8",
    )
    with pytest.raises(CatalogError, match="conflicts with a configured profile"):
        ModelCatalog.load(str(path))


@pytest.mark.parametrize("content, message", [
    ("[models.bad]\nmodel = 'm'\nargs = ['--port', '9']\n", "must not set --model or --port"),
    ("[models.bad]\nmodel = 'm'\ncmd = 'anything'\n", "unsupported keys"),
    ("[models.bad]\nmodel = ''\n", "non-empty string"),
    ("[models.bad]\nmodel = 'm'\nport = -1\n", "0 through 65535"),
])
def test_catalog_rejects_ambiguous_or_shell_style_profiles(tmp_path, content, message):
    path = tmp_path / "models.toml"
    path.write_text(content, encoding="utf-8")
    with pytest.raises(CatalogError, match=message):
        ModelCatalog.load(str(path))


def test_catalog_unknown_profile_has_operator_facing_error():
    with pytest.raises(CatalogError, match="unknown model profile 'missing'"):
        ModelCatalog.empty().get("missing")


def test_catalog_marks_port_zero_as_an_explicit_dynamic_port(tmp_path):
    path = tmp_path / "models.toml"
    path.write_text("[models.dynamic]\nmodel = 'm'\nport = 0\n", encoding="utf-8")
    profile = ModelCatalog.load(str(path)).get("dynamic")
    assert profile.port == 0
    assert profile.public()["dynamicPort"] is True


def test_catalog_resolves_collision_safe_aliases_and_hides_unlisted_models(tmp_path):
    path = tmp_path / "models.toml"
    path.write_text(
        """[router]
include_aliases_in_list = true

[models.visible]
model = "visible.gguf"
aliases = ["nickname", "compat-id"]

[models.hidden]
model = "hidden.gguf"
aliases = ["private-name"]
unlisted = true
""",
        encoding="utf-8",
    )

    catalog = ModelCatalog.load(str(path))

    assert catalog.get("nickname") is catalog.get("visible")
    assert catalog.get("private-name") is catalog.get("hidden")
    assert catalog.listed_model_ids() == ("visible", "nickname", "compat-id")
    default_listing = ModelCatalog({
        "visible": catalog.get("visible"),
        "hidden": catalog.get("hidden"),
    })
    assert default_listing.listed_model_ids() == ("visible",)
    public = {profile["name"]: profile for profile in catalog.public()}
    assert public["visible"]["aliases"] == ["nickname", "compat-id"]
    assert public["hidden"]["unlisted"] is True


@pytest.mark.parametrize(
    "models,message",
    [
        (
            "[models.one]\nmodel='one.gguf'\naliases=['two']\n"
            "[models.two]\nmodel='two.gguf'\n",
            "conflicts with a configured profile",
        ),
        (
            "[models.one]\nmodel='one.gguf'\naliases=['shared']\n"
            "[models.two]\nmodel='two.gguf'\naliases=['shared']\n",
            "assigned to both",
        ),
        ("[models.one]\nmodel='one.gguf'\naliases=['bad//name']\n", "distinct valid"),
    ],
)
def test_catalog_rejects_ambiguous_or_invalid_model_aliases(tmp_path, models, message):
    path = tmp_path / "models.toml"
    path.write_text(models, encoding="utf-8")
    with pytest.raises(CatalogError, match=message):
        ModelCatalog.load(str(path))


@pytest.mark.parametrize("model_id", ["bad//name", "bad/../name", "/bad"])
def test_catalog_rejects_unsafe_namespaced_model_ids(tmp_path, model_id):
    path = tmp_path / "models.toml"
    path.write_text(
        f'[models."{model_id}"]\nmodel = "model.gguf"\n', encoding="utf-8"
    )
    with pytest.raises(CatalogError, match="slash-separated"):
        ModelCatalog.load(str(path))


def test_catalog_accepts_colon_variant_model_ids(tmp_path):
    path = tmp_path / "models.toml"
    path.write_text(
        '[models."coding:high"]\nmodel = "coding.gguf"\n', encoding="utf-8"
    )
    assert ModelCatalog.load(str(path)).get("coding:high").name == "coding:high"


def test_catalog_validates_pin_and_warm_selectors(tmp_path):
    path = tmp_path / "models.toml"
    path.write_text(
        """[models.a]
model = "a.gguf"
aliases = ["a:variant"]
[models.b]
model = "b.gguf"

[selectors.public]
strategy = "pin"
targets = ["a:variant", "b"]
name = "Public Model"
description = "Stable local model"
[selectors.public.metadata]
tier = "stable"
type = "operator-value"

[selectors.available]
strategy = "warm"
targets = ["a", "b"]

[selectors.hidden]
strategy = "pin"
targets = ["a"]
unlisted = true
""",
        encoding="utf-8",
    )

    catalog = ModelCatalog.load(str(path))

    assert catalog.selector("public").targets == ("a:variant", "b")
    assert catalog.selector("available").strategy == "warm"
    assert catalog.public_selectors() == [
        {"name": "available", "strategy": "warm", "targets": ["a", "b"]},
        {"name": "hidden", "strategy": "pin", "targets": ["a"], "unlisted": True},
        {
            "name": "public", "strategy": "pin", "targets": ["a:variant", "b"],
            "displayName": "Public Model", "description": "Stable local model",
            "metadata": {"tier": "stable", "type": "operator-value"},
        },
    ]
    assert catalog.listed_model_ids() == ("a", "b", "available", "public")


def test_catalog_validates_runtime_routing_profiles_and_selector_targets(tmp_path):
    path = tmp_path / "models.toml"
    path.write_text(
        """[models.a]
model = "a.gguf"
aliases = ["a:variant"]

[selectors.available]
strategy = "warm"
targets = ["a"]

[profiles.coding]
description = "Coding mode"
[profiles.coding.pins]
public = "available"
direct = "a:variant"
disabled = ""
""",
        encoding="utf-8",
    )

    catalog = ModelCatalog.load(str(path))

    profile = catalog.routing_profile("coding")
    assert profile.replacement("public") == (True, "available")
    assert profile.replacement("disabled") == (True, None)
    assert profile.replacement("other") == (False, None)
    assert catalog.public_routing_profiles() == [{
        "name": "coding",
        "description": "Coding mode",
        "pins": {"direct": "a:variant", "disabled": None, "public": "available"},
    }]


@pytest.mark.parametrize("content,message", [
    ('[profiles.empty]\npins = {}\n', "must contain at least one"),
    (
        '[profiles.bad.pins]\npublic = "missing"\n',
        "references unknown model",
    ),
    ('[profiles.bad.pins]\npublic = 7\n', "model ID or empty string"),
    ('[profiles."bad/name".pins]\npublic = "a"\n', "profile name"),
])
def test_catalog_rejects_invalid_runtime_routing_profiles(tmp_path, content, message):
    path = tmp_path / "models.toml"
    path.write_text('[models.a]\nmodel = "a.gguf"\n' + content, encoding="utf-8")
    with pytest.raises(CatalogError, match=message):
        ModelCatalog.load(str(path))


@pytest.mark.parametrize("content,message", [
    (
        '[selectors.bad]\nstrategy = "spillover"\ntargets = ["a"]\n',
        "requires multi-resident or peer capacity",
    ),
    ('[selectors.bad]\nstrategy = "random"\ntargets = ["a"]\n', "pin or warm"),
    ('[selectors.bad]\nstrategy = "pin"\ntargets = []\n', "1 to 64"),
    (
        '[selectors.bad]\nstrategy = "pin"\ntargets = ["a"]\n'
        '[selectors.bad.metadata]\ncreated = 2026-09-14\n',
        "JSON-compatible",
    ),
    ('[selectors.bad]\nstrategy = "pin"\ntargets = ["missing"]\n', "not a configured"),
    ('[selectors.a]\nstrategy = "pin"\ntargets = ["a"]\n', "conflicts"),
    (
        '[selectors.first]\nstrategy = "pin"\ntargets = ["second"]\n'
        '[selectors.second]\nstrategy = "warm"\ntargets = ["a"]\n',
        "cannot reference another selector",
    ),
])
def test_catalog_rejects_unsupported_or_ambiguous_selectors(
    tmp_path, content, message
):
    path = tmp_path / "models.toml"
    path.write_text('[models.a]\nmodel = "a.gguf"\n' + content, encoding="utf-8")
    with pytest.raises(CatalogError, match=message):
        ModelCatalog.load(str(path))


def test_catalog_supports_namespaced_model_ids_and_longest_upstream_prefix(tmp_path):
    path = tmp_path / "models.toml"
    path.write_text(
        """[router]
include_aliases_in_list = true

[models.author]
model = "parent.gguf"

[models."author/model"]
model = "exact.gguf"
aliases = ["org/compat"]
""",
        encoding="utf-8",
    )
    catalog = ModelCatalog.load(str(path))

    assert catalog.get("org/compat").name == "author/model"
    assert catalog.listed_model_ids() == ("author", "author/model", "org/compat")
    requested, profile, remaining = catalog.resolve_upstream_path("author/model/api/x/y")
    assert (requested, profile.name, remaining) == (
        "author/model", "author/model", "/api/x/y",
    )
    requested, profile, remaining = catalog.resolve_upstream_path("org/compat")
    assert (requested, profile.name, remaining) == ("org/compat", "author/model", "/")
    with pytest.raises(CatalogError, match="does not begin"):
        catalog.resolve_upstream_path("missing/model/v1/chat")


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
    path.write_text("[models.coding]\nmodel = '/models/coding.gguf'\nport = 1922\ncheck_endpoint = '/ready'\nargs = ['--max-seq-len-override', '32768']\n", encoding="utf-8")

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
        def fresh_readiness(self, port, target):
            assert target == "/ready"
            return {"reachable": True, "ready": True, "port": port}

    manager = Manager()
    with ThreadPoolExecutor(1) as lifecycle, ThreadPoolExecutor(1) as proxy:
        app = build_app(
            manager=manager, ring=LogRing(), probe=Probe(), footprint_fn=lambda pid: {},
            lifecycle_pool=lifecycle, proxy_pool=proxy, catalog=ModelCatalog.load(str(path)), token="secret",
        )
        client = TestClient(app)
        assert client.get("/router/profiles").status_code == 401
        listing = client.get("/router/profiles", headers={"X-FT-Token": "secret"})
        assert listing.status_code == 200
        assert listing.json()["data"][0]["name"] == "coding"
        public_listing = client.get("/models")
        assert public_listing.status_code == 200
        assert public_listing.json()["data"][0]["id"] == "coding"
        assert "/models/coding.gguf" not in public_listing.text
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


def test_client_models_uses_authenticated_profile_control_route(monkeypatch, capsys):
    seen = {}

    def request(method, url, path, **kwargs):
        seen.update(method=method, url=url, path=path, **kwargs)
        return {"data": [{"name": "coding"}]}

    monkeypatch.setattr(daemon_client, "_request_json", request)
    assert daemon_client.main([
        "models", "--url", "http://daemon:1900", "--token", "control-secret"
    ]) == 0
    assert seen == {
        "method": "GET", "url": "http://daemon:1900", "path": "/router/profiles",
        "body": None, "token": "control-secret", "timeout": daemon_client.DEFAULT_TIMEOUT,
    }
    assert '"name": "coding"' in capsys.readouterr().out


def test_readiness_supports_a_validated_non_health_endpoint():
    class Manager:
        def status(self):
            return {"running": True, "pid": 44}

    class Probe:
        def fresh_readiness(self, port, path):
            assert (port, path) == (1922, "/ready")
            return {"reachable": True, "ready": True}

    result = wait_for_ready(
        Manager(), Probe(), pid=44, port=1922, timeout_s=1, path="/ready"
    )
    assert result == {"ready": True, "health": {"reachable": True, "ready": True}}


def test_router_policy_is_strict_and_public_model_fields_are_safe(tmp_path):
    path = tmp_path / "models.toml"
    path.write_text("""
[router]
api_keys = ["one", "two"]
default_ttl_s = 300
unload_timeout_s = 45
upstream_timeout_s = 42
scheduler = "fifo"
global_concurrency_limit = 4
send_loading_state = true

[router.groups.interactive]
members = ["coding", "chat"]
swap = true
exclusive = true

[models.coding]
model = "coding.gguf"
ttl_s = 0
unload_timeout_s = 60
priority = 10
concurrency_limit = 2
send_loading_state = false
group = "interactive"

[models.chat]
model = "chat.gguf"
priority = -5
""", encoding="utf-8")
    catalog = ModelCatalog.load(str(path))
    assert catalog.settings.api_keys == ("one", "two")
    assert catalog.settings.default_ttl_s == 300
    assert catalog.settings.upstream_timeout_s == 42
    assert catalog.settings.global_concurrency_limit == 4
    assert catalog.settings.send_loading_state is True
    assert catalog.settings.groups[0].members == ("coding", "chat")
    public = {item["name"]: item for item in catalog.public()}
    assert public["coding"] == {
        "name": "coding", "model": "coding.gguf", "args": [], "readyTimeoutS": 120.0,
        "ttlS": 0.0, "unloadTimeoutS": 60.0, "priority": 10,
        "group": "interactive", "concurrencyLimit": 2, "sendLoadingState": False,
    }
    assert "api_keys" not in str(public)


@pytest.mark.parametrize("router, message", [
    ("[router]\nscheduler = 'lifo'", "scheduler"),
    ("[router]\nupstream_timeout_s = 0", "upstream_timeout_s"),
    ("drop_fields = ['model']", "drop_fields"),
    ("[router]\napi_keys = ['same', 'same']", "duplicates"),
    ("[router]\ninclude_aliases_in_list = 'yes'", "include_aliases_in_list"),
    ("[router]\nglobal_concurrency_limit = -1", "global_concurrency_limit"),
    ("[router]\nsend_loading_state = 'yes'", "send_loading_state"),
    ("concurrency_limit = true", "concurrency_limit"),
    ("send_loading_state = 1", "send_loading_state"),
    ('[router.groups."bad/name"]\nmembers = ["a"]', "router group names"),
    ("[router.groups.g]\nmembers = ['missing']", "configured models"),
    ("[router.groups.g]\nmembers = ['a']\npersistent = true", "persistent"),
    ("[router.groups.g]\nmembers = ['a']\nexclusive = false", "exclusive"),
    ("[router.groups.g]\nmembers = ['a']\nswap = false", "multi-resident"),
    ("[models.b]\nmodel = 'b.gguf'\n[router.groups.g]\nmembers = ['a', 'b']\npersistent = true\nswap = false", "exactly one"),
    ("group = 'other'", "must match"),
])
def test_router_policy_rejects_ambiguous_or_unsafe_configuration(tmp_path, router, message):
    path = tmp_path / "models.toml"
    path.write_text("[models.a]\nmodel = 'a.gguf'\n" + router, encoding="utf-8")
    with pytest.raises(CatalogError, match=message):
        ModelCatalog.load(str(path))


def test_router_policy_accepts_a_singleton_persistent_protected_slot(tmp_path):
    path = tmp_path / "models.toml"
    path.write_text("""
[router.groups.resident]
members = ["a"]
swap = false
exclusive = true
persistent = true

[models.a]
model = "a.gguf"
group = "resident"
""", encoding="utf-8")
    group = ModelCatalog.load(str(path)).settings.groups[0]
    assert (group.members, group.swap, group.exclusive, group.persistent) == (("a",), False, True, True)
