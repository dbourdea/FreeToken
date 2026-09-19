"""Swap boundary regressions, runnable without the GPU runtime."""
# What: document swap boundary regressions runnable without the in the test_swap_regressions docstring; why: introspection and maintainers read this exact docstring fragment to understand test swap regressions behavior without executing it.

# What: import ast for test readiness http contract using ast; why: test_readiness_http_contract uses ast parse, making that imported dependency available to its named operation.
import ast
# What: import json for test routing profile client uses atomic selection endpoint using json; why: test_routing_profile_client_uses_atomic_selection_endpoint uses json loads, making that imported dependency available to its named operation.
import json
# What: import threading for test profile readiness failure recovery end to end using threading; why: test_profile_readiness_failure_recovery_end_to_end uses threading event, making that imported dependency available to its named operation.
import threading
# What: import thread pool executor for test profile readiness failure recovery end to end using concurrent and futures and thread pool executor; why: test_profile_readiness_failure_recovery_end_to_end uses thread pool executor, making that imported dependency available to its named operation.
from concurrent.futures import ThreadPoolExecutor
# What: import path for test readiness http contract using pathlib and path; why: test_readiness_http_contract uses path, making that imported dependency available to its named operation.
from pathlib import Path

# What: import pytest for module initialization using pytest; why: module initialization uses pytest mark parametrize, making that imported dependency available to its named operation.
import pytest
# What: import fast api for test readiness http contract using fastapi and fast api; why: test_readiness_http_contract uses fast api, making that imported dependency available to its named operation.
from fastapi import FastAPI
# What: import test client for test readiness http contract using fastapi and testclient and test client; why: test_readiness_http_contract uses test client, making that imported dependency available to its named operation.
from fastapi.testclient import TestClient

# What: arrange from freetoken daemon catalog import CatalogError ModelCatalog for the scenario; why: test swap regressions requires this concrete input or helper state before exercising the behavior under test.
from freetoken.daemon.catalog import CatalogError, ModelCatalog
# What: arrange from freetoken daemon import client as daemon client for the scenario; why: test swap regressions requires this concrete input or helper state before exercising the behavior under test.
from freetoken.daemon import client as daemon_client
# What: import wait for ready for test readiness rechecks generation after probe using freetoken and daemon and readiness and wait for ready; why: test_readiness_rechecks_generation_after_probe uses wait for ready, making that imported dependency available to its named operation.
from freetoken.daemon.readiness import wait_for_ready
# What: import serve probe for test fresh health does not reuse previous model cache using freetoken and daemon and proxy and serve probe; why: test_fresh_health_does_not_reuse_previous_model_cache uses serve probe, making that imported dependency available to its named operation.
from freetoken.daemon.proxy import ServeProbe
# What: import build app for test profile readiness failure recovery end to end using freetoken and daemon and app and build app; why: test_profile_readiness_failure_recovery_end_to_end uses build app, making that imported dependency available to its named operation.
from freetoken.daemon.app import build_app
# What: import log ring for test switch launch recovery is 503 not success using freetoken and daemon and logring and log ring; why: test_switch_launch_recovery_is_503_not_success uses log ring, making that imported dependency available to its named operation.
from freetoken.daemon.logring import LogRing
# What: import switch launch error for switch using freetoken and daemon and serve manager and switch launch error; why: switch uses switch launch error, making that imported dependency available to its named operation.
from freetoken.daemon.serve_manager import SwitchLaunchError
# What: arrange from tests daemon test daemon serve manager import Spawner make manager for the scenario; why: test daemon serve manager import spawner make manager in test requires this concrete input or helper state before exercising the behavior under test.
from tests.daemon.test_daemon_serve_manager import Spawner, make_manager


# What: parameterize test_profile_readiness_failure_recovery_end_to_end with the listed cases; why: pytest reruns the same arrange, act, and assertions for each input protecting test profile readiness failure recovery end to end.
@pytest.mark.parametrize("failure", ["error", "timeout", "operator-stop", "recovery-error"])
# What: define the test_profile_readiness_failure_recovery_end_to_end test around tmp path and failure; why: this test groups the arrange, act, and assertions that protect the profile readiness failure recovery end to end outcome.
def test_profile_readiness_failure_recovery_end_to_end(tmp_path, failure):
    # What: act by calling Spawner and capture sp; why: the profile readiness failure recovery end to end test asserts the response, state, or failure produced by this call.
    sp = Spawner()
    # What: act by calling make_manager and capture manager and and ring; why: the profile readiness failure recovery end to end test asserts the response, state, or failure produced by this call.
    manager, _, ring = make_manager(tmp_path, sp,
                                   # What: act by evaluating signal fn lambda pid sig sp by pid pid die; why: test swap regressions test profile readiness failure recovery end to end captures the behavior or response that its following assertions inspect.
                                   signal_fn=lambda pid, sig: sp.by_pid(pid).die())
    # What: arrange the exact manager start previous original fixture fragment; why: the profile readiness failure recovery end to end scenario feeds this byte-preserved fragment through manager.start("previous", 1922, ["--original"]) before asserting its protocol or parser result.
    manager.start("previous", 1922, ["--original"])
    # What: arrange path as tmp path and models and toml; why: the profile readiness failure recovery end to end test consumes this named precondition before exercising the behavior.
    path = tmp_path / "models.toml"
    # What: arrange the exact path write text models bad nmodel replacement nport nready timeout s fixture fragment; why: the profile readiness failure recovery end to end scenario feeds this byte-preserved fragment through path.write_text("[models.bad]\nmodel = 'replacement'\nport = 1923\nready before asserting its p.
    path.write_text("[models.bad]\nmodel = 'replacement'\nport = 1923\nready_timeout_s = 1\n",
                    # What: arrange the exact encoding utf 8 fixture fragment; why: the profile readiness failure recovery end to end scenario feeds this byte-preserved fragment through encoding="utf-8") before asserting its protocol or parser result.
                    encoding="utf-8")
    # What: act by calling threading.Event and capture entered and release; why: the profile readiness failure recovery end to end test asserts the response, state, or failure produced by this call.
    entered, release = threading.Event(), threading.Event()

    # What: define Probe as the owner of fresh_health; why:  daemon callers use this class boundary so those methods share one probe state invariant.
    class Probe:
        # What: arrange the def fresh health self port test helper boundary; why: test swap regressions test profile readiness failure recovery end to end uses this local double to isolate the behavior checked by its assertions.
        def fresh_health(self, port):
            # What: act on port before status and failure; why: the profile readiness failure recovery end to end scenario admits status and failure only for this predicate and excludes the opposite state.
            if port == 1922:
                # What: arrange status as failure and error and ok and recovery error; why: the profile readiness failure recovery end to end test consumes this named precondition before exercising the behavior.
                status = "error" if failure == "recovery-error" else "ok"
            # What: act on failure before set and entered; why: the profile readiness failure recovery end to end scenario admits set and entered only for this predicate and excludes the opposite state.
            elif failure == "operator-stop":
                # What: act by calling entered.set with the declared inputs; why: the profile readiness failure recovery end to end scenario observes the entered.set return value during assert release wait.
                entered.set()
                # What: assert that release wait 5; why: this assertion protects the profile readiness failure recovery end to end regression after the test's arranged inputs and exercised call.
                assert release.wait(5)
                # What: arrange status as error; why: the profile readiness failure recovery end to end test consumes this named precondition before exercising the behavior.
                status = "error"
            # What: select the remaining branch that performs status loading if failure timeout else; why: fresh_health covers the state excluded by the preceding predicate without conflating the two outcomes.
            else:
                # What: arrange status as failure and loading and error and timeout; why: the profile readiness failure recovery end to end test consumes this named precondition before exercising the behavior.
                status = "loading" if failure == "timeout" else "error"
            # What: arrange the helper response as reachable True status status maintenance serving; why: test swap regressions test profile readiness failure recovery end to end feeds this result into the behavior whose outcome is asserted.
            return {"reachable": True, "status": status, "maintenance": "serving"}

    # What: enter the ThreadPoolExecutor and ThreadPoolExecutor managed context before app build app manager manager ring ring; why: test_profile_readiness_failure_recovery_end_to_end releases this resource or lock after app build app manager manager ring ring on both success and failure paths.
    with ThreadPoolExecutor(1) as lifecycle, ThreadPoolExecutor(1) as proxy:
        # What: act by calling build_app and capture app; why: the profile readiness failure recovery end to end test asserts the response, state, or failure produced by this call.
        app = build_app(manager=manager, ring=ring, probe=Probe(),
                        # What: arrange footprint fn lambda pid lifecycle pool lifecycle for the scenario; why: test swap regressions test profile readiness failure recovery end to end requires this concrete input or helper state before exercising the behavior under test.
                        footprint_fn=lambda pid: {}, lifecycle_pool=lifecycle,
                        # What: arrange proxy pool to ModelCatalog.load; why: the profile readiness failure recovery end to end scenario binds this proxy value to ModelCatalog.load's proxy pool input.
                        proxy_pool=proxy, catalog=ModelCatalog.load(str(path)))
        # What: arrange with TestClient app as client ThreadPoolExecutor 1 as requests for the scenario; why: test client app as client thread pool executor 1 as in test requires this concrete input or helper state before exercising the behavior under test.
        with TestClient(app) as client, ThreadPoolExecutor(1) as requests:
            # What: act by calling requests.submit and capture response task; why: the profile readiness failure recovery end to end test asserts the response, state, or failure produced by this call.
            response_task = requests.submit(client.post, "/engine/switch-profile", json={"name": "bad"})
            # What: act on failure before wait and status code and set and entered and release; why: the profile readiness failure recovery end to end scenario admits wait and status code and set and entered and release only for this predicate and excludes the opposite state.
            if failure == "operator-stop":
                # What: establish the handler boundary for the protected operation; why: test_profile_readiness_failure_recovery_end_to_end routes failures to the unconditional cleanup block while preserving cleanup and success flow.
                try:
                    # What: assert that entered wait 5; why: this assertion protects the profile readiness failure recovery end to end regression after the test's arranged inputs and exercised call.
                    assert entered.wait(5)
                    # The only proxy worker is blocked, but lifecycle remains available.
                    # What: assert that client post engine stop json status code equals 200; why: this assertion protects the profile readiness failure recovery end to end regression after the test's arranged inputs and exercised call.
                    assert client.post("/engine/stop", json={}).status_code == 200
                # What: run release set on every exit path; why: test_profile_readiness_failure_recovery_end_to_end performs this cleanup after success, rejection, or exception so resources and accounting cannot remain stranded.
                finally:
                    # What: act by calling release.set with the declared inputs; why: the profile readiness failure recovery end to end scenario observes the release.set return value during response response task result timeout.
                    release.set()
            # What: act by calling response_task.result and capture response; why: the profile readiness failure recovery end to end test asserts the response, state, or failure produced by this call.
            response = response_task.result(timeout=10)
    # What: assert that response status code equals 503; why: this assertion protects the profile readiness failure recovery end to end regression after the test's arranged inputs and exercised call.
    assert response.status_code == 503
    # What: act by calling response.json and capture doc; why: the profile readiness failure recovery end to end test asserts the response, state, or failure produced by this call.
    doc = response.json()
    # What: assert that doc readiness ready is false; why: this assertion protects the profile readiness failure recovery end to end regression after the test's arranged inputs and exercised call.
    assert not doc["readiness"]["ready"]
    # What: act on failure before doc; why: the profile readiness failure recovery end to end scenario admits doc only for this predicate and excludes the opposite state.
    if failure == "operator-stop":
        # What: assert that doc rollback reason equals superseded; why: this assertion protects the profile readiness failure recovery end to end regression after the test's arranged inputs and exercised call.
        assert doc["rollback"]["reason"] == "superseded"
        # What: assert that manager status running is false; why: this assertion protects the profile readiness failure recovery end to end regression after the test's arranged inputs and exercised call.
        assert not manager.status()["running"]
    # What: select the remaining branch that performs assert doc rollback launched; why: test_profile_readiness_failure_recovery_end_to_end covers the state excluded by the preceding predicate without conflating the two outcomes.
    else:
        # What: assert that doc rollback launched; why: this assertion protects the profile readiness failure recovery end to end regression after the test's arranged inputs and exercised call.
        assert doc["rollback"]["launched"]
        # What: assert that doc rollback readiness ready is failure differs from recovery error; why: this assertion protects the profile readiness failure recovery end to end regression after the test's arranged inputs and exercised call.
        assert doc["rollback"]["readiness"]["ready"] is (failure != "recovery-error")
        # What: assert that manager status model equals previous; why: this assertion protects the profile readiness failure recovery end to end regression after the test's arranged inputs and exercised call.
        assert manager.status()["model"] == "previous"
        # What: act by calling manager.stop with the declared inputs; why: the profile readiness failure recovery end to end scenario observes the manager.stop return value during the enclosing return.
        manager.stop()


# What: parameterize test_switch_launch_recovery_is_503_not_success with the listed cases; why: pytest reruns the same arrange, act, and assertions for each input protecting test switch launch recovery is 503 not success.
@pytest.mark.parametrize("route,body", [
    # What: arrange the model field as bad; why: test_switch_launch_recovery_is_503_not_success sends this field through ("/engine/switch", {"model": "bad"}) so the router selects the canonical model or alias for upstream dispatch.
    ("/engine/switch", {"model": "bad"}),
    # What: arrange the name field as bad; why: test_switch_launch_recovery_is_503_not_success carries name into ("/engine/switch-profile", {"name": "bad"}).
    ("/engine/switch-profile", {"name": "bad"}),
# What: arrange the pytest.mark.parametrize call with ordered positional inputs; why: test_switch_launch_recovery_is_503_not_success groups the supplied clauses as one pytest.mark.parametrize call before its value is consumed.
])
# What: define the test_switch_launch_recovery_is_503_not_success test around tmp path and route and body; why: this test groups the arrange, act, and assertions that protect the switch launch recovery is 503 not success outcome.
def test_switch_launch_recovery_is_503_not_success(tmp_path, route, body):
    # What: arrange path as tmp path and models and toml; why: the switch launch recovery is 503 not success test consumes this named precondition before exercising the behavior.
    path = tmp_path / "models.toml"
    # What: arrange the exact path write text models bad nmodel bad n encoding fixture fragment; why: the switch launch recovery is 503 not success scenario feeds this byte-preserved fragment through path.write_text("[models.bad]\nmodel = 'bad'\n", encoding="utf-8") before asserting its protocol or parser result.
    path.write_text("[models.bad]\nmodel = 'bad'\n", encoding="utf-8")

    # What: define Manager as the owner of status and switch; why: daemon callers use this class boundary so those methods share one manager state invariant.
    class Manager:
        # What: define the status test helper around captured fixture state; why: the switch launch recovery is 503 not success scenario calls this helper to produce or observe the exact behavior checked by its assertions.
        def status(self):
            # What: arrange the port field as 1922; why: Manager.status carries port into return {"port": 1922}.
            return {"port": 1922}

        # What: define the switch test helper around captured fixture state; why: the switch launch recovery is 503 not success scenario calls this helper to produce or observe the exact behavior checked by its assertions.
        def switch(self, *args):
            # What: raise SwitchLaunchError for the caller; why: Manager.switch stops this rejected path before it can mutate state, dispatch work, or report success.
            raise SwitchLaunchError(OSError("failed"),
                                    # What: arrange the attempted field as true; why: Manager.switch carries attempted into {"attempted": True, "launched": True, "pid": 42}, None).
                                    {"attempted": True, "launched": True, "pid": 42}, None)

        # What: arrange switch for readiness as switch; why: the switch launch recovery is 503 not success test consumes this named precondition before exercising the behavior.
        switch_for_readiness = switch

    # What: enter the ThreadPoolExecutor and ThreadPoolExecutor managed context before app build app manager manager ring log ring; why: test_switch_launch_recovery_is_503_not_success releases this resource or lock after app build app manager manager ring log ring on both success and failure paths.
    with ThreadPoolExecutor(1) as lifecycle, ThreadPoolExecutor(1) as proxy:
        # What: act by calling build_app and capture app; why: the switch launch recovery is 503 not success test asserts the response, state, or failure produced by this call.
        app = build_app(manager=Manager(), ring=LogRing(), probe=None,
                        # What: arrange the pid input for test_switch_launch_recovery_is_503_not_success; why: test_switch_launch_recovery_is_503_not_success consumes pid during signature binding, so callers must bind it with the other signature inputs.
                        footprint_fn=lambda pid: {}, lifecycle_pool=lifecycle,
                        # What: arrange proxy pool to ModelCatalog.load; why: the switch launch recovery is 503 not success scenario binds this proxy value to ModelCatalog.load's proxy pool input.
                        proxy_pool=proxy, catalog=ModelCatalog.load(str(path)))
        # What: enter the TestClient managed context before response client post route json body; why: test_switch_launch_recovery_is_503_not_success releases this resource or lock after response client post route json body on both success and failure paths.
        with TestClient(app) as client:
            # What: act by calling client.post and capture response; why: the switch launch recovery is 503 not success test asserts the response, state, or failure produced by this call.
            response = client.post(route, json=body)
    # What: assert that response status code equals 503; why: this assertion protects the switch launch recovery is 503 not success regression after the test's arranged inputs and exercised call.
    assert response.status_code == 503
    # What: assert that response json code equals switch launch failed; why: this assertion protects the switch launch recovery is 503 not success regression after the test's arranged inputs and exercised call.
    assert response.json()["code"] == "switch_launch_failed"
    # What: assert that response json rollback launched is true; why: this assertion protects the switch launch recovery is 503 not success regression after the test's arranged inputs and exercised call.
    assert response.json()["rollback"]["launched"] is True
    # What: assert that ready is absent from response json rollback; why: this assertion protects the switch launch recovery is 503 not success regression after the test's arranged inputs and exercised call.
    assert "ready" not in response.json()["rollback"]


# What: parameterize test_catalog_rejects_owned_option_aliases with the listed cases; why: pytest reruns the same arrange, act, and assertions for each input protecting test catalog rejects owned option aliases.
@pytest.mark.parametrize("arg", ["--model-path", "--model-path=other", "--model-p", "--mod=other", "--por=8", "--"])
# What: define the test_catalog_rejects_owned_option_aliases test around tmp path and arg; why: this test groups the arrange, act, and assertions that protect the catalog rejects owned option aliases outcome.
def test_catalog_rejects_owned_option_aliases(tmp_path, arg):
    # What: arrange path as tmp path and models and toml; why: the catalog rejects owned option aliases test consumes this named precondition before exercising the behavior.
    path = tmp_path / "models.toml"
    # What: arrange the exact path write text f models bad nmodel m nargs fixture fragment; why: the catalog rejects owned option aliases scenario feeds this byte-preserved fragment through path.write_text(f"[models.bad]\nmodel = 'm'\nargs = ['{arg}']\n", encodi before asserting its protocol or parser result.
    path.write_text(f"[models.bad]\nmodel = 'm'\nargs = ['{arg}']\n", encoding="utf-8")
    # What: assert the pytest.raises failure context; why: the catalog rejects owned option aliases scenario rejects the unsafe input through this exact exception boundary.
    with pytest.raises(CatalogError, match="must not set"):
        # What: act by calling ModelCatalog.load with str and path; why: the catalog rejects owned option aliases scenario observes the ModelCatalog.load return value during the enclosing return.
        ModelCatalog.load(str(path))


# What: define the test_readiness_rechecks_generation_after_probe test around local fixtures; why: this test groups the arrange, act, and assertions that protect the readiness rechecks generation after probe outcome.
def test_readiness_rechecks_generation_after_probe():
    # What: define Manager as the owner of status; why: daemon callers use this class boundary so those methods share one manager state invariant.
    class Manager:
        # What: arrange pid as 44; why: the readiness rechecks generation after probe test consumes this named precondition before exercising the behavior.
        pid = 44

        # What: define the status test helper around captured fixture state; why: the readiness rechecks generation after probe scenario calls this helper to produce or observe the exact behavior checked by its assertions.
        def status(self):
            # What: arrange the running field as true; why: Manager.status carries running into return {"running": True, "pid": self.pid}.
            return {"running": True, "pid": self.pid}

    # What: act by calling Manager and capture manager; why: the readiness rechecks generation after probe test asserts the response, state, or failure produced by this call.
    manager = Manager()

    # What: define Probe as the owner of fresh_health; why:  daemon callers use this class boundary so those methods share one probe state invariant.
    class Probe:
        # What: define an uncached health probe for the active engine port; why: readiness checks must bypass a replaced generation's cached response before accepting the new process.
        def fresh_health(self, port):
            # What: arrange pid as 45; why: the readiness rechecks generation after probe test consumes this named precondition before exercising the behavior.
            manager.pid = 45
            # What: arrange the reachable field as true; why: Probe.fresh_health carries reachable into return {"reachable": True, "status": "ok"}.
            return {"reachable": True, "status": "ok"}

    # What: act by calling wait_for_ready and capture result; why: the readiness rechecks generation after probe test asserts the response, state, or failure produced by this call.
    result = wait_for_ready(manager, Probe(), pid=44, port=1922, timeout_s=1)
    # What: assert that result ready is false; why: this assertion protects the readiness rechecks generation after probe regression after the test's arranged inputs and exercised call.
    assert result["ready"] is False
    # What: assert that result reason equals superseded; why: this assertion protects the readiness rechecks generation after probe regression after the test's arranged inputs and exercised call.
    assert result["reason"] == "superseded"


# What: define the test_profile_client_reports_legacy_readiness_failure test around monkeypatch; why: this test groups the arrange, act, and assertions that protect the profile client reports legacy readiness failure outcome.
def test_profile_client_reports_legacy_readiness_failure(monkeypatch):
    # What: arrange seen as the fixture input; why: the profile client reports legacy readiness failure test consumes this named precondition before exercising the behavior.
    seen = {}

    # What: define the request test helper around captured fixture state; why: the profile client reports legacy readiness failure scenario calls this helper to produce or observe the exact behavior checked by its assertions.
    def request(*args, **kwargs):
        # What: act by calling seen.update with kwargs; why: the profile client reports legacy readiness failure scenario observes the seen.update return value during return readiness ready reason engine error.
        seen.update(kwargs)
        # What: arrange the readiness field as ready and reason and false and engine error; why: request carries readiness into return {"readiness": {"ready": False, "reason": "engine-error"}}.
        return {"readiness": {"ready": False, "reason": "engine-error"}}

    # What: arrange the exact monkeypatch setattr daemon client request json request fixture fragment; why: the profile client reports legacy readiness failure scenario feeds this byte-preserved fragment through monkeypatch.setattr(daemon_client, "_request_json", request) before asserting its protocol or parser result.
    monkeypatch.setattr(daemon_client, "_request_json", request)
    # What: assert that daemon client main start profile coding equals 1; why: this assertion protects the profile client reports legacy readiness failure regression after the test's arranged inputs and exercised call.
    assert daemon_client.main(["start-profile", "coding"]) == 1
    # What: assert that seen timeout equals daemon client default profile timeout; why: this assertion protects the profile client reports legacy readiness failure regression after the test's arranged inputs and exercised call.
    assert seen["timeout"] == daemon_client.DEFAULT_PROFILE_TIMEOUT


# What: parameterize test_routing_profile_client_uses_atomic_selection_endpoint with the listed cases; why: pytest reruns the same arrange, act, and assertions for each input protecting test routing profile client uses atomic selection endpoint.
@pytest.mark.parametrize("argv,expected_body", [
    # What: arrange the name field as coding; why: test_routing_profile_client_uses_atomic_selection_endpoint carries name into (["activate-routing-profile", "coding"], {"name": "coding"}).
    (["activate-routing-profile", "coding"], {"name": "coding"}),
    # What: arrange the name field as the fixture input; why: test_routing_profile_client_uses_atomic_selection_endpoint carries name into (["clear-routing-profile"], {"name": None}).
    (["clear-routing-profile"], {"name": None}),
# What: arrange the pytest.mark.parametrize call with ordered positional inputs; why: test_routing_profile_client_uses_atomic_selection_endpoint groups the supplied clauses as one pytest.mark.parametrize call before its value is consumed.
])
# What: define the test_routing_profile_client_uses_atomic_selection_endpoint test around monkeypatch and capsys and argv and expected body; why: this test groups the arrange, act, and assertions that protect the routing profile client uses atomic selection endpoint outcome.
def test_routing_profile_client_uses_atomic_selection_endpoint(
    # What: arrange the monkeypatch input for test_routing_profile_client_uses_atomic_selection_endpoint; why: test_routing_profile_client_uses_atomic_selection_endpoint consumes monkeypatch during monkeypatch setattr daemon client request json request, so callers must bind it with the other signature inputs.
    monkeypatch, capsys, argv, expected_body
# What: arrange the grouped source fragment for the scenario; why: test routing profile client uses atomic selection endpoint requires this concrete input or helper state before exercising the behavior under test.
):
    # What: arrange seen as the fixture input; why: the routing profile client uses atomic selection endpoint test consumes this named precondition before exercising the behavior.
    seen = {}

    # What: define the request test helper around method and url and path; why: the routing profile client uses atomic selection endpoint scenario calls this helper to produce or observe the exact behavior checked by its assertions.
    def request(method, url, path, **kwargs):
        # What: arrange method to seen.update; why: the routing profile client uses atomic selection endpoint scenario binds this method value to seen.update's method input.
        seen.update(method=method, url=url, path=path, **kwargs)
        # What: arrange the active field as expected body and name; why: request carries active into return {"active": expected_body["name"]}.
        return {"active": expected_body["name"]}

    # What: arrange the exact monkeypatch setattr daemon client request json request fixture fragment; why: the routing profile client uses atomic selection endpoint scenario feeds this byte-preserved fragment through monkeypatch.setattr(daemon_client, "_request_json", request) before asserting its protocol or parser.
    monkeypatch.setattr(daemon_client, "_request_json", request)

    # What: assert that daemon client main argv equals 0; why: this assertion protects the routing profile client uses atomic selection endpoint regression after the test's arranged inputs and exercised call.
    assert daemon_client.main(argv) == 0
    # What: assert that seen method equals put; why: this assertion protects the routing profile client uses atomic selection endpoint regression after the test's arranged inputs and exercised call.
    assert seen["method"] == "PUT"
    # What: assert that seen path equals router profiles active; why: this assertion protects the routing profile client uses atomic selection endpoint regression after the test's arranged inputs and exercised call.
    assert seen["path"] == "/router/profiles/active"
    # What: assert that seen body equals expected body; why: this assertion protects the routing profile client uses atomic selection endpoint regression after the test's arranged inputs and exercised call.
    assert seen["body"] == expected_body
    # What: assert that json loads capsys readouterr out active equals expected body name; why: this assertion protects the routing profile client uses atomic selection endpoint regression after the test's arranged inputs and exercised call.
    assert json.loads(capsys.readouterr().out)["active"] == expected_body["name"]


# What: define the test_fresh_health_does_not_reuse_previous_model_cache test around local fixtures; why: this test groups the arrange, act, and assertions that protect the fresh health does not reuse previous model cache outcome.
def test_fresh_health_does_not_reuse_previous_model_cache():
    # What: act by calling iter and capture docs; why: the fresh health does not reuse previous model cache test asserts the response, state, or failure produced by this call.
    docs = iter([{"status": "ok", "instance_id": "old"}, {"status": "loading", "instance_id": "new"}])
    # What: act by calling ServeProbe and capture probe; why: the fresh health does not reuse previous model cache test asserts the response, state, or failure produced by this call.
    probe = ServeProbe(opener=lambda *_: next(docs), ttl_s=100)
    # What: assert that probe health 1922 status equals ok; why: this assertion protects the fresh health does not reuse previous model cache regression after the test's arranged inputs and exercised call.
    assert probe.health(1922)["status"] == "ok"
    # What: assert that probe fresh health 1922 status equals loading; why: this assertion protects the fresh health does not reuse previous model cache regression after the test's arranged inputs and exercised call.
    assert probe.fresh_health(1922)["status"] == "loading"


# What: parameterize test_readiness_http_contract with the listed cases; why: pytest reruns the same arrange, act, and assertions for each input protecting test readiness http contract.
@pytest.mark.parametrize("status,maintenance,expected", [
    # What: arrange the loading error portion of the enclosing predicate; why: this clause remains in the readiness http contract scenario\'s enclosing expression so its grouping and evaluation order stay intact.
    ("loading", None, 503), ("error", None, 503),
    # What: arrange the ok draining ok serving portion of the enclosing predicate; why: this clause remains in the readiness http contract scenario\'s enclosing expression so its grouping and evaluation order stay intact.
    ("ok", "draining", 503), ("ok", "serving", 200),
# What: arrange the pytest.mark.parametrize call with ordered positional inputs; why: test_readiness_http_contract groups the supplied clauses as one pytest.mark.parametrize call before its value is consumed.
])
# What: define the test_readiness_http_contract test around status and maintenance and expected; why: this test groups the arrange, act, and assertions that protect the readiness http contract outcome.
def test_readiness_http_contract(status, maintenance, expected):
    # Execute the actual handlers, excluding unrelated torch-dependent metrics
    # imports. This is a CPU contract test, not a full serving integration test.
    # What: act by calling Path and capture source; why: the readiness http contract test asserts the response, state, or failure produced by this call.
    source = Path(__file__).parents[2] / "python/freetoken/server/control_api.py"
    # What: act by calling ast.parse and capture module; why: the readiness http contract test asserts the response, state, or failure produced by this call.
    module = ast.parse(source.read_text(encoding="utf-8"))
    # What: act by calling next and capture register; why: the readiness http contract test asserts the response, state, or failure produced by this call.
    register = next(n for n in module.body if isinstance(n, ast.FunctionDef) and n.name == "register_control_routes")
    # What: act by calling isinstance and capture routes; why: the readiness http contract test asserts the response, state, or failure produced by this call.
    routes = [n for n in register.body if isinstance(n, ast.AsyncFunctionDef) and n.name in {"health", "ready"}]
    # What: act by calling FastAPI and capture app; why: the readiness http contract test asserts the response, state, or failure produced by this call.
    app = FastAPI()
    # What: arrange doc as status and maintenance and status and maintenance; why: the readiness http contract test consumes this named precondition before exercising the behavior.
    doc = {"status": status, "maintenance": maintenance}
    # What: arrange namespace as app and doc and app and build health and get state; why: the readiness http contract test consumes this named precondition before exercising the behavior.
    namespace = {"app": app, "build_health": lambda *_: doc, "get_state": lambda: None}
    # What: arrange the exact exec compile ast module body routes type ignores fixture fragment; why: the readiness http contract scenario feeds this byte-preserved fragment through exec(compile(ast.Module(body=routes, type_ignores=[]), str(source), "exe before asserting its protocol or parser result.
    exec(compile(ast.Module(body=routes, type_ignores=[]), str(source), "exec"), namespace)
    # What: enter the TestClient managed context before assert client get health status code; why: test_readiness_http_contract releases this resource or lock after assert client get health status code on both success and failure paths.
    with TestClient(app) as client:
        # What: assert that client get health status code equals 200; why: this assertion protects the readiness http contract regression after the test's arranged inputs and exercised call.
        assert client.get("/health").status_code == 200
        # What: act by calling client.get and capture response; why: the readiness http contract test asserts the response, state, or failure produced by this call.
        response = client.get("/ready")
        # What: assert that response status code equals expected; why: this assertion protects the readiness http contract regression after the test's arranged inputs and exercised call.
        assert response.status_code == expected
        # What: assert that response json equals doc; why: this assertion protects the readiness http contract regression after the test's arranged inputs and exercised call.
        assert response.json() == doc
