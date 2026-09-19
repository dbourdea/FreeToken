"""Opt-in Linux maintenance-window qualification against a real llama-swap binary.

Artifacts contain local operational paths and raw model output. Keep them private.
This script never changes the protected service's configuration or enablement.
"""
# What: document opt in linux maintenance window qualification against a in the qualify docstring; why: introspection and maintainers read this exact docstring fragment to understand qualify behavior without executing it.
# What: document artifacts contain local operational paths and in the qualify docstring; why: introspection and maintainers read this exact docstring fragment to understand qualify behavior without executing it.
# What: document this script never changes the protected in the qualify docstring; why: introspection and maintainers read this exact docstring fragment to understand qualify behavior without executing it.
# What: preserve the paragraph boundary in the the qualify docstring; why: introspection and maintainers read this paragraph break to understand qualify behavior without executing it.

# What: import argparse for main using argparse; why: main uses argparse argument parser, making that imported dependency available to its named operation.
import argparse
# What: import json for cancellation canary using json; why: cancellation_canary uses json loads, making that imported dependency available to its named operation.
import json
# What: import os for main using os; why: main uses os environ copy, making that imported dependency available to its named operation.
import os
# What: import path for main using pathlib and path; why: main uses path, making that imported dependency available to its named operation.
from pathlib import Path
# What: import signal for main using signal; why: main uses signal signal, making that imported dependency available to its named operation.
import signal
# What: import socket for require expected hostname using socket; why: require_expected_hostname uses socket gethostname, making that imported dependency available to its named operation.
import socket
# What: import subprocess for main using subprocess; why: main uses subprocess run, making that imported dependency available to its named operation.
import subprocess
# What: import sys for module initialization using sys; why: module initialization uses sys exit, making that imported dependency available to its named operation.
import sys
# What: import time for cancellation canary using time; why: cancellation_canary uses time monotonic, making that imported dependency available to its named operation.
import time
# What: import urllib error for http using urllib and error; why: http uses urllib request request, making that imported dependency available to its named operation.
import urllib.error
# What: import urllib request for http using urllib and request; why: http uses urllib request request, making that imported dependency available to its named operation.
import urllib.request
# What: import thread pool executor for main using concurrent and futures and thread pool executor; why: main uses thread pool executor, making that imported dependency available to its named operation.
from concurrent.futures import ThreadPoolExecutor


# What: define require_expected_hostname and its declared inputs; why: callers use require_expected_hostname to perform the behavior named by this helper without duplicating its boundary checks.
def require_expected_hostname(expected: str, *, actual: str | None = None) -> str:
    """Fail closed unless the operator names this exact maintenance host.

    The mismatch deliberately omits both values so a copied error cannot publish
    a private machine name. The approved public hardware label is documented
    separately and is not assumed to equal the operating-system hostname.
    """
    # What: document fail closed unless the operator names in the require_expected_hostname docstring; why: introspection and maintainers read this exact docstring fragment to understand require expected hostname behavior without executing it.
    # What: document the mismatch deliberately omits both values in the require_expected_hostname docstring; why: introspection and maintainers read this exact docstring fragment to understand require expected hostname behavior without executing it.
    # What: document a private machine name the approved in the require_expected_hostname docstring; why: introspection and maintainers read this exact docstring fragment to understand require expected hostname behavior without executing it.
    # What: document separately and is not assumed to in the require_expected_hostname docstring; why: introspection and maintainers read this exact docstring fragment to understand require expected hostname behavior without executing it.
    # What: preserve the paragraph boundary in the the require_expected_hostname docstring; why: introspection and maintainers read this paragraph break to understand require expected hostname behavior without executing it.
    # What: compute actual from actual and gethostname and socket; why: if not expected or x00 in later reads actual, so require_expected_hostname must retain the computed value under that name.
    actual = socket.gethostname() if actual is None else actual
    # What: gate on expected and actual before runtime error; why: require_expected_hostname admits runtime error only for this predicate and excludes the opposite state.
    if not expected or "\x00" in expected or actual != expected:
        # What: raise RuntimeError for the caller; why: require_expected_hostname stops this rejected path before it can mutate state, dispatch work, or report success.
        raise RuntimeError(
            # What: execute qualification host does not match the operator supplied expected hostname; why: the enclosing symbol requires this operation for its concrete qualification or routing path.
            "qualification host does not match the operator-supplied expected hostname"
        # What: complete the RuntimeError call with ordered positional inputs; why: require_expected_hostname groups the supplied clauses as one RuntimeError call before its value is consumed.
        )
    # What: return the hostname that passed exact-host validation; why: callers use this confirmed identity before any maintenance side effect is allowed.
    return actual


# What: define http around url and body and timeout; why: its direct callers call http for http and rely on this exact input and result contract.
def http(url, body=None, timeout=30):
    # What: compute data from body and encode and dumps and json; why: request urllib request request url data data headers later reads data, so http must retain the computed value under that name.
    data = None if body is None else json.dumps(body).encode()
    # What: map the content type field as application and json; why: http carries content type through request into with urllib request urlopen request timeout timeout as response.
    request = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    # What: enter the urllib.request.urlopen managed context before return response read; why: http releases this resource or lock after return response read on both success and failure paths.
    with urllib.request.urlopen(request, timeout=timeout) as response:
        # What: return read and response from http; why: http exposes read and response so its caller can continue with the function\'s computed outcome.
        return response.read()


# What: define wait_health around url and seconds; why: its direct callers call wait_health for wait health and rely on this exact input and result contract.
def wait_health(url, seconds):
    # What: compute deadline from seconds and monotonic and time; why: while time monotonic deadline later reads deadline, so wait_health must retain the computed value under that name.
    deadline = time.monotonic() + seconds
    # What: iterate across deadline and monotonic and time to perform doc and loads and oserror and value error and json; why: wait_health repeats the body only while or for the loop header admits an iteration.
    while time.monotonic() < deadline:
        # What: establish the handler boundary for the protected operation; why: wait_health routes failures to oserror and value error while preserving cleanup and success flow.
        try:
            # What: compute doc from loads and json and http and url and 3; why: if doc get status ok later reads doc, so wait_health must retain the computed value under that name.
            doc = json.loads(http(url, timeout=3))
            # What: gate on get and doc before doc; why: wait_health admits doc only for this predicate and excludes the opposite state.
            if doc.get("status") == "ok":
                # What: return doc from wait_health; why: wait_health exposes doc so its caller can continue with the function\'s computed outcome.
                return doc
        # What: handle oserror and value error by pass; why: wait_health converts that failure into this concrete recovery, response, or cleanup behavior.
        except (OSError, ValueError):
            # What: ignore the anticipated exception handled by this branch; why: wait_health continues its retry or cleanup path instead of re-raising that transient failure.
            pass
        # What: pause one second between health probes; why: wait_health avoids a busy retry loop while retaining a bounded readiness deadline.
        time.sleep(1)
    # What: raise TimeoutError for the caller; why: wait_health stops this rejected path before it can mutate state, dispatch work, or report success.
    raise TimeoutError("health did not become ready")


# What: define canary around url and model and stream; why: its direct callers call canary for canary and rely on this exact input and result contract.
def canary(url, model, stream=False):
    # What: compute body from model and stream and model and messages and temperature; why: body stream options include usage later reads body, so canary must retain the computed value under that name.
    body = {
        # What: map the model field as model; why: canary sends this field through body so the router selects the canonical model or alias for upstream dispatch.
        "model": model,
        # What: map the role field as user; why: canary carries role through body into body stream options include usage true.
        "messages": [{"role": "user", "content": "What is 2 + 2? Reply with only the single digit."}],
        # What: map the temperature field as 0; why: canary carries temperature through body into body stream options include usage true.
        "temperature": 0, "max_tokens": 32, "stream": stream,
        # What: map the enable thinking field as false; why: canary carries enable thinking through body into body stream options include usage true.
        "chat_template_kwargs": {"enable_thinking": False},
    # What: complete the body mapping with model and messages and temperature and max tokens and stream; why: canary groups the supplied clauses as one body mapping before its value is consumed.
    }
    # What: gate on stream before body; why: canary admits body only for this predicate and excludes the opposite state.
    if stream:
        # What: map the include usage field as true; why: canary carries include usage through body entry into raw http url v1 chat completions body.
        body["stream_options"] = {"include_usage": True}
    # What: compute raw from http and body and url and v1 and chat; why: assert b data done in raw later reads raw, so canary must retain the computed value under that name.
    raw = http(url + "/v1/chat/completions", body, timeout=660)
    # What: gate on stream before parts; why: canary admits parts only for this predicate and excludes the opposite state.
    if stream:
        # What: initialize parts as an empty runtime accumulator; why: canary appends or maps entries into it during parts append choice get delta get content or before consuming the aggregate.
        parts = []
        # What: assert that b data done is present in raw; why: canary requires b data done is present in raw to be true, so a false result stops the invalid state.
        assert b"data: [DONE]" in raw, "SSE completion marker missing"
        # What: iterate across splitlines and decode and raw to perform doc and choice and startswith and line and loads; why: canary repeats the body only while or for the loop header admits an iteration.
        for line in raw.decode().splitlines():
            # What: gate on startswith and line before doc and loads and json and line; why: canary admits doc and loads and json and line only for this predicate and excludes the opposite state.
            if line.startswith("data: ") and line != "data: [DONE]":
                # What: compute doc from loads and json and line and 6; why: for choice in doc get choices later reads doc, so canary must retain the computed value under that name.
                doc = json.loads(line[6:])
                # What: iterate across get and doc to perform append and parts and get and choice; why: canary repeats the body only while or for the loop header admits an iteration.
                for choice in doc.get("choices", []):
                    # What: preserve the exact parts append choice get delta get content or literal fragment; why: canary passes this fragment verbatim through parts.append(choice.get("delta", {}).get("content") or ""), because changing it would alter a protocol payload, serialized fixture, or public message.
                    parts.append(choice.get("delta", {}).get("content") or "")
        # What: compute content from join and parts and value; why: content doc choices message get content later reads content, so canary must retain the computed value under that name.
        content = "".join(parts)
    # What: select the remaining branch that performs doc json loads raw; why: canary covers the state excluded by the preceding predicate without conflating the two outcomes.
    else:
        # What: compute doc from loads and raw and json; why: content doc choices message get content later reads doc, so canary must retain the computed value under that name.
        doc = json.loads(raw)
        # What: compute content from get and doc and value and content and message; why: return raw content strip later reads content, so canary must retain the computed value under that name.
        content = doc["choices"][0]["message"].get("content") or ""
    # What: return raw and strip and content from canary; why: canary exposes raw and strip and content so its caller can continue with the function\'s computed outcome.
    return raw, content.strip()


# What: define cancellation_canary around url and model and seconds; why: its direct callers call cancellation_canary for cancellation canary and rely on this exact input and result contract.
def cancellation_canary(url, model, *, seconds=30):
    """Close a live SSE response, then require same-process terminal abort evidence.

    Active reaching zero alone is insufficient: TTL restart and normal completion
    can also produce that observation. Check instance identity and completed count.
    """
    # What: document close a live sse response then in the cancellation_canary docstring; why: introspection and maintainers read this exact docstring fragment to understand cancellation canary behavior without executing it.
    # What: document active reaching zero alone is insufficient in the cancellation_canary docstring; why: introspection and maintainers read this exact docstring fragment to understand cancellation canary behavior without executing it.
    # What: document can also produce that observation check in the cancellation_canary docstring; why: introspection and maintainers read this exact docstring fragment to understand cancellation canary behavior without executing it.
    # What: preserve the paragraph boundary in the the cancellation_canary docstring; why: introspection and maintainers read this paragraph break to understand cancellation canary behavior without executing it.
    # What: compute stats url from model and url and v1 and stats and upstream; why: before json loads http stats url later reads stats url, so cancellation_canary must retain the computed value under that name.
    stats_url = url + "/upstream/" + model + "/v1/stats"
    # What: compute before from loads and json and http and stats url; why: instance before get instance id later reads before, so cancellation_canary must retain the computed value under that name.
    before = json.loads(http(stats_url))
    # What: compute instance from get and before and instance id; why: assert instance backend instance identity missing later reads instance, so cancellation_canary must retain the computed value under that name.
    instance = before.get("instance_id")
    # What: assert that instance; why: cancellation_canary requires instance to be true, so a false result stops the invalid state.
    assert instance, "backend instance identity missing"
    # What: assert that before requests active equals 0; why: cancellation_canary requires before requests active equals 0 to be true, so a false result stops the invalid state.
    assert before["requests"]["active"] == 0, "cancellation test requires an idle backend"
    # What: map the model field as model; why: cancellation_canary sends this field through body so the router selects the canonical model or alias for upstream dispatch.
    body = {"model": model, "stream": True, "max_tokens": 1024, "temperature": 0,
            # What: map the role field as user; why: cancellation_canary carries role through body into data json dumps body encode.
            "messages": [{"role": "user", "content":
                          # What: apply the count from to writing every number portion of body; why: cancellation_canary uses this clause to evaluate body as one grouped value.
                          "Count from 1 to 1000, writing every number on a separate line. Do not summarize."}],
            # What: map the enable thinking field as false; why: cancellation_canary carries enable thinking through body into data json dumps body encode.
            "chat_template_kwargs": {"enable_thinking": False}}
    # What: compute request from request and request and url and urllib; why: with urllib request urlopen request timeout as response later reads request, so cancellation_canary must retain the computed value under that name.
    request = urllib.request.Request(url + "/v1/chat/completions",
                                     # What: supply data to operation.encode; why: cancellation_canary binds this encode and dumps and body and json value to operation.encode's data input.
                                     data=json.dumps(body).encode(),
                                     # What: map the content type field as application and json; why: cancellation_canary carries content type through request into with urllib request urlopen request timeout 660 as response.
                                     headers={"Content-Type": "application/json"})
    # What: compute raw from bytearray; why: raw extend line later reads raw, so cancellation_canary must retain the computed value under that name.
    raw = bytearray()
    # What: compute started from monotonic and time; why: after after first content seconds first content started later reads started, so cancellation_canary must retain the computed value under that name.
    started = time.monotonic()
    # What: initialize the observed-statistics sentinel to no result; why: cancellation_canary can distinguish not-yet-fetched state from a completed statistics response.
    observed = None
    # What: enter the urllib.request.urlopen managed context before for line in response; why: cancellation_canary releases this resource or lock after for line in response on both success and failure paths.
    with urllib.request.urlopen(request, timeout=660) as response:
        # Read incrementally. Reading the entire body would only test completion.
        # What: iterate across response to perform extend and line and raw; why: cancellation_canary repeats the body only while or for the loop header admits an iteration.
        for line in response:
            # What: append the received stream line to the raw response buffer; why: cancellation_canary tracks accumulated bytes before triggering its disconnect threshold.
            raw.extend(line)
            # What: gate on len and raw before runtime error; why: cancellation_canary admits runtime error only for this predicate and excludes the opposite state.
            if len(raw) > 1024 * 1024:
                # What: raise RuntimeError for the caller; why:  cancellation_canary stops this rejected path before it can mutate state, dispatch work, or report success.
                raise RuntimeError("stream exceeded cancellation capture limit")
            # What: gate on strip and line before runtime error; why: cancellation_canary admits runtime error only for this predicate and excludes the opposite state.
            if line.strip() == b"data: [DONE]":
                # What: raise RuntimeError for the caller; why:  cancellation_canary stops this rejected path before it can mutate state, dispatch work, or report success.
                raise RuntimeError("stream completed before cancellation")
            # What: gate on startswith and line before the computed value; why: cancellation_canary admits the computed value only for this predicate and excludes the opposite state.
            if not line.startswith(b"data: "):
                # What: apply the continue portion of the enclosing predicate; why: this clause remains in cancellation_canary\'s enclosing expression so its grouping and evaluation order stay intact.
                continue
            # What: compute doc from loads and json and line and 6; why: if any choice get delta get content later reads doc, so cancellation_canary must retain the computed value under that name.
            doc = json.loads(line[6:])
            # What: gate on any and get and choice and doc before first content and monotonic and time; why: cancellation_canary admits first content and monotonic and time only for this predicate and excludes the opposite state.
            if any(choice.get("delta", {}).get("content") for choice in doc.get("choices", [])):
                # What: compute first content from monotonic and time; why: after after first content seconds first content started later reads first content, so cancellation_canary must retain the computed value under that name.
                first_content = time.monotonic()
                # What: compute observed from loads and json and http and stats url; why: assert observed instance id instance backend restarted later reads observed, so cancellation_canary must retain the computed value under that name.
                observed = json.loads(http(stats_url))
                # What: assert that observed instance id equals instance; why: cancellation_canary requires observed instance id equals instance to be true, so a false result stops the invalid state.
                assert observed["instance_id"] == instance, "backend restarted before disconnect"
                # What: assert that observed requests active exceeds 0; why: cancellation_canary requires observed requests active exceeds 0 to be true, so a false result stops the invalid state.
                assert observed["requests"]["active"] > 0, "generation already finished before disconnect"
                # What: leave the stream loop after enough response bytes arrive; why: cancellation can now be triggered against a live partial response.
                break
        # What: select the remaining branch that performs raise runtime error stream ended without a; why: cancellation_canary covers the state excluded by the preceding predicate without conflating the two outcomes.
        else:
            # What: raise RuntimeError for the caller; why:  cancellation_canary stops this rejected path before it can mutate state, dispatch work, or report success.
            raise RuntimeError("stream ended without a content delta")
    # What: compute disconnected from monotonic and time; why: deadline disconnected seconds later reads disconnected, so cancellation_canary must retain the computed value under that name.
    disconnected = time.monotonic()
    # What: compute deadline from disconnected and seconds; why: if time monotonic deadline later reads deadline, so cancellation_canary must retain the computed value under that name.
    deadline = disconnected + seconds
    # What: poll cancellation statistics until a terminal result; why: the loop ends after cancellation evidence or its explicit deadline.
    while True:
        # What: compute after from loads and json and http and stats url; why: assert after instance id instance backend restart later reads after, so cancellation_canary must retain the computed value under that name.
        after = json.loads(http(stats_url))
        # What: assert that after instance id equals instance; why: cancellation_canary requires after instance id equals instance to be true, so a false result stops the invalid state.
        assert after["instance_id"] == instance, "backend restart cannot count as cancellation"
        # What: gate on after before after and before; why: cancellation_canary admits after and before only for this predicate and excludes the opposite state.
        if after["requests"]["active"] == 0:
            # What: require after requests completed == before requests completed; why: the qualifier stops immediately when this protected invariant is false.
            # What: require after requests completed == before requests completed; why: the qualifier stops immediately when this protected invariant is false.
            assert after["requests"]["completed"] == before["requests"]["completed"], \
                "normal completion cannot count as cancellation"
            # What: map the passed field as true; why: cancellation_canary carries passed into return bytes(raw), {"passed": True, "before": before, "during": observed.
            return bytes(raw), {"passed": True, "before": before, "during": observed,
                                # What: map the after field as after; why: cancellation_canary carries after into "after": after, "firstContentSeconds": first_content - started.
                                "after": after, "firstContentSeconds": first_content - started,
                                # What: map the abort seconds field as disconnected and monotonic and time; why: cancellation_canary carries abort seconds into "abortSeconds": time.monotonic() - disconnected}.
                                "abortSeconds": time.monotonic() - disconnected}
        # What: gate on deadline and monotonic and time before timeout error; why: cancellation_canary admits timeout error only for this predicate and excludes the opposite state.
        if time.monotonic() >= deadline:
            # What: raise TimeoutError for the caller; why: cancellation_canary stops this rejected path before it can mutate state, dispatch work, or report success.
            raise TimeoutError("disconnected request did not reach terminal abort")
        # What: call time.sleep with 0 25; why: cancellation_canary invokes time.sleep while performing the enclosing return; the call advances that operation through its result or side effect.
        time.sleep(0.25)


# What: define main around the current object state; why: its direct callers call main for main and rely on this exact input and result contract.
def main():
    # What: compute parser from argument parser and argparse and doc; why: parser add argument name required later reads parser, so main must retain the computed value under that name.
    parser = argparse.ArgumentParser(description=__doc__)
    # What: iterate across the computed value to perform add argument and parser and name; why: main repeats the body only while or for the loop header admits an iteration.
    for name in ("source", "python", "llama-swap", "model-a", "model-b", "artifacts", "protected-service", "protected-url", "expected-hostname"):
        # What: preserve the exact parser add argument name required literal fragment; why: main passes this fragment verbatim through parser.add_argument("--" + name, required=True), because changing it would alter a protocol payload, serialized fixture, or public message.
        parser.add_argument("--" + name, required=True)
    # What: register the parser add argument allow maintenance action store true required True command-line option; why: main validates this operator input before starting the qualification sequence.
    parser.add_argument("--allow-maintenance", action="store_true", required=True)
    # What: register the parser add argument port type int default 1960 command-line option; why: main validates this operator input before starting the qualification sequence.
    parser.add_argument("--port", type=int, default=1960)
    # What: preserve the exact parser add argument start port type int default literal fragment; why: main passes this fragment verbatim through parser.add_argument("--start-port", type=int, default=1961), because changing it would alter a protocol payload, serialized fixture, or public message.
    parser.add_argument("--start-port", type=int, default=1961)
    # What: add the --extended switch for concurrency and idle-eviction checks; why: operators opt into the longer qualification cases instead of running them by default.
    parser.add_argument("--extended", action="store_true", help="Also test concurrent requests and idle eviction")
    # What: add the --cancellation switch for live SSE disconnect checks; why: operators explicitly request the disruptive cancellation-and-recovery qualification path.
    parser.add_argument("--cancellation", action="store_true", help="Also qualify live SSE disconnect and recovery")
    # What: compute args from parse args and parser; why: require expected hostname args expected hostname later reads args, so main must retain the computed value under that name.
    args = parser.parse_args()
    # What: call require_expected_hostname with expected hostname and args; why: main invokes require_expected_hostname while performing artifacts path args artifacts; the call advances that operation through its result or side effect.
    require_expected_hostname(args.expected_hostname)
    # What: compute artifacts from path and artifacts and args; why: artifacts mkdir parents exist ok later reads artifacts, so main must retain the computed value under that name.
    artifacts = Path(args.artifacts)
    # What: supply parents to artifacts.mkdir; why: main binds this true value to artifacts.mkdir's parents input.
    artifacts.mkdir(parents=True, exist_ok=False)
    # What: map the trials field as the fixture input; why: main carries trials through status into artifacts result json write text json dumps status indent 2.
    status = {"trials": [], "restored": False}

    # What: define save around the current object state; why: its direct callers call save for save and rely on this exact input and result contract.
    def save():
        # What: write the current qualification status as indented UTF-8 JSON; why: operators need a durable result artifact even when a later qualification phase fails.
        (artifacts / "result.json").write_text(json.dumps(status, indent=2), encoding="utf-8")

    # What: compute service from sudo and n and systemctl; why: subprocess run service is active quiet args protected service check later reads service, so main must retain the computed value under that name.
    service = ["sudo", "-n", "systemctl"]
    # What: execute subprocess run service is active quiet args protected service check True; why: the enclosing symbol requires this operation for its concrete qualification or routing path.
    subprocess.run(service + ["is-active", "--quiet", args.protected_service], check=True)
    # What: compute status entry from wait health and protected url and args and 10 and health; why: status trials append row later reads status entry, so main must retain the computed value under that name.
    status["baselineHealth"] = wait_health(args.protected_url + "/health", 10)
    # What: compute baseline models from loads and json and http and protected url; why: protected model baseline models data id later reads baseline models, so main must retain the computed value under that name.
    baseline_models = json.loads(http(args.protected_url + "/v1/models"))
    # What: compute protected model from baseline models and id and 0 and data; why: raw content canary args protected url protected model later reads protected model, so main must retain the computed value under that name.
    protected_model = baseline_models["data"][0]["id"]
    # What: evaluate and capture raw content canary args protected url protected model; why: the enclosing qualifier uses the captured result in its next validation or artifact step.
    raw, content = canary(args.protected_url, protected_model)
    # What: execute artifacts baseline json write bytes raw; why: the enclosing symbol requires this operation for its concrete qualification or routing path.
    (artifacts / "baseline.json").write_bytes(raw)
    # What: gate on content before runtime error; why: main admits runtime error only for this predicate and excludes the opposite state.
    if content != "4":
        # What: raise RuntimeError for the caller; why:  main stops this rejected path before it can mutate state, dispatch work, or report success.
        raise RuntimeError("protected-service baseline canary did not return 4; no maintenance performed")

    # What: compute env from copy and environ and os; why: env pythonpath str path args source python later reads env, so main must retain the computed value under that name.
    env = os.environ.copy()
    # What: compute env entry from str and path and source and args and python; why: env path str path home local bin later reads env entry, so main must retain the computed value under that name.
    env["PYTHONPATH"] = str(Path(args.source) / "python")
    # What: compute env entry from pathsep and get and str and os; why: env torch extensions dir str artifacts torch extensions later reads env entry, so main must retain the computed value under that name.
    env["PATH"] = str(Path.home() / ".local/bin") + os.pathsep + env.get("PATH", "")
    # Avoid sharing extension binaries or abandoned build locks across revisions.
    # What: compute env entry from str and artifacts and torch extensions; why: env max jobs later reads env entry, so main must retain the computed value under that name.
    env["TORCH_EXTENSIONS_DIR"] = str(artifacts / "torch-extensions")
    # What: cap native-extension compilation at two parallel jobs; why: the later kernel preflight must not exhaust the qualification host while building extensions.
    env["MAX_JOBS"] = "2"
    # What: compute config from start port and args and health check timeout and global ttl and unload timeout; why: config f alias cmd json dumps command later reads config, so main must retain the computed value under that name.
    config = ["healthCheckTimeout: 600", "globalTTL: 0", "unloadTimeout: 45", "logToStdout: both", f"startPort: {args.start_port}", "models:"]
    # What: import shlex for main using shlex; why: main uses shlex join, making that imported dependency available to its named operation.
    import shlex

    # What: iterate across model a and model b and args to perform command and join and shlex and python and model; why: main repeats the body only while or for the loop header admits an iteration.
    for alias, model in (("model-a", args.model_a), ("model-b", args.model_b)):
        # What: compute command from join and shlex and python and model; why: config f alias cmd json dumps command later reads command, so main must retain the computed value under that name.
        command = shlex.join([
            # What: apply the args python m freetoken cli serve model model portion of command; why: main uses this clause to evaluate command as one grouped value.
            args.python, "-m", "freetoken.cli", "serve", "--model", model,
            # What: apply the host port port served model name model id portion of command; why: main uses this clause to evaluate command as one grouped value.
            "--host", "127.0.0.1", "--port", "${PORT}", "--served-model-name", "${MODEL_ID}",
            # What: apply the max seq len override num tokens max prefill length portion of command; why: main uses this clause to evaluate command as one grouped value.
            "--max-seq-len-override", "4096", "--num-tokens", "4096", "--max-prefill-length", "512",
            # What: apply the max running requests graph memory ratio portion of command; why: main uses this clause to evaluate command as one grouped value.
            "--max-running-requests", "1", "--graph", "1", "--memory-ratio", "0.75",
            # What: apply the attention backend triton moe backend fused disable pynccl portion of command; why: main uses this clause to evaluate command as one grouped value.
            "--attention-backend", "triton", "--moe-backend", "fused", "--disable-pynccl",
        # What: complete the shlex.join call with python; why: main groups the supplied clauses as one shlex.join call before its value is consumed.
        ])
        # What: append this model command, readiness endpoint, and proxy stanza; why: the generated llama-swap configuration needs a complete entry before optional TTL settings.
        config += [f"  {alias}:", "    cmd: " + json.dumps(command), "    checkEndpoint: /ready", "    proxy: http://127.0.0.1:${PORT}"]
        # What: gate on extended and args before append and config; why: main admits append and config only for this predicate and excludes the opposite state.
        if args.extended:
            # What: preserve the exact config append ttl literal fragment; why: main passes this fragment verbatim through config.append(" ttl: 5"), because changing it would alter a protocol payload, serialized fixture, or public message.
            config.append("    ttl: 5")
    # What: compute config path from artifacts and models and yaml; why: config path write text n join config n encoding later reads config path, so main must retain the computed value under that name.
    config_path = artifacts / "models.yaml"
    # What: preserve the exact config path write text n join config n encoding literal fragment; why: main passes this fragment verbatim through config_path.write_text("\n".join(config) + "\n", encoding="utf-8"), because changing it would alter a protocol payload, serialized fixture, or public message.
    config_path.write_text("\n".join(config) + "\n", encoding="utf-8")
    # What: run llama-swap configuration validation against the generated file; why: qualification fails before launch when the temporary routing configuration is invalid.
    subprocess.run([args.llama_swap, "-config", str(config_path), "-validate"], env=env, check=True)
    # What: preserve the exact print native kernel preflight started flush literal fragment; why: main passes this fragment verbatim through print("NATIVE_KERNEL_PREFLIGHT_STARTED", flush=True), because changing it would alter a protocol payload, serialized fixture, or public message.
    print("NATIVE_KERNEL_PREFLIGHT_STARTED", flush=True)
    # What: open the with artifacts kernel build log open wb as build log resource scope; why: the qualification operation releases this resource when the guarded block exits.
    with (artifacts / "kernel-build.log").open("wb") as build_log:
        # What: execute subprocess run args python c from freetoken kernel gguf import  module  module print NATIVE KERNEL READY; why: the enclosing symbol requires this operation for its concrete qualification or routing path.
        subprocess.run([args.python, "-c", "from freetoken.kernel.gguf import _module; _module(); print('NATIVE_KERNEL_READY')"],
                       # What: supply env to subprocess.run; why: main binds this env value to subprocess.run's env input.
                       env=env, cwd=args.source, stdout=build_log, stderr=subprocess.STDOUT, check=True, timeout=600)
    # What: initialize the child-process sentinel to no process; why: cleanup can test whether llama-swap started before attempting termination.
    proc = None
    # What: compute maintenance from false; why: maintenance later reads maintenance, so main must retain the computed value under that name.
    maintenance = False

    # What: define interrupted around the current object state; why: its direct callers call interrupted for interrupted and rely on this exact input and result contract.
    def interrupted(*_):
        # What: convert a termination signal into KeyboardInterrupt; why: the normal interruption path then performs restoration and child cleanup.
        raise KeyboardInterrupt

    # What: register the interruption handler for SIGTERM; why: service-manager termination must enter the qualifier restoration path.
    signal.signal(signal.SIGTERM, interrupted)
    # What: register the interruption handler for SIGHUP; why: session loss must enter the same restoration path.
    signal.signal(signal.SIGHUP, interrupted)
    # What: establish the handler boundary for the protected operation; why: main routes failures to base exception while preserving cleanup and success flow.
    try:
        # Set the restore obligation before the stop, including partial failures.
        # What: compute maintenance from true; why: if maintenance later reads maintenance, so main must retain the computed value under that name.
        maintenance = True
        # What: execute subprocess run service stop args protected service check True timeout 90; why: the enclosing symbol requires this operation for its concrete qualification or routing path.
        subprocess.run(service + ["stop", args.protected_service], check=True, timeout=90)
        # What: preserve the exact print maintenance started flush literal fragment; why: main passes this fragment verbatim through print("MAINTENANCE_STARTED", flush=True), because changing it would alter a protocol payload, serialized fixture, or public message.
        print("MAINTENANCE_STARTED", flush=True)
        # What: enter the operation.open managed context before proc subprocess popen args llama swap config str config path; why: main releases this resource or lock after proc subprocess popen args llama swap config str config path on both success and failure paths.
        with (artifacts / "swap.log").open("wb") as log:
            # What: compute proc from popen and subprocess and llama swap and env; why: if time monotonic deadline or proc poll is later reads proc, so main must retain the computed value under that name.
            proc = subprocess.Popen([args.llama_swap, "-config", str(config_path), "-listen", f"127.0.0.1:{args.port}"],
                                    # What: supply env to subprocess.Popen; why: main binds this env value to subprocess.Popen's env input.
                                    env=env, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
            # What: compute base from port and args and http; why: listing json loads http base v1 models later reads base, so main must retain the computed value under that name.
            base = f"http://127.0.0.1:{args.port}"
            # What: compute deadline from monotonic and time and 20; why: if time monotonic deadline or proc poll is later reads deadline, so main must retain the computed value under that name.
            deadline = time.monotonic() + 20
            # What: retry model-list readiness until a terminal condition; why: the loop exits on a valid listing and raises on process exit or deadline expiry.
            while True:
                # What: establish the handler boundary for the protected operation; why: main routes failures to oserror and value error while preserving cleanup and success flow.
                try:
                    # What: compute listing from loads and json and http and base and v1; why: assert item id for item in later reads listing, so main must retain the computed value under that name.
                    listing = json.loads(http(base + "/v1/models", timeout=2))
                    # What: assert that item id for item in listing equals model a model b; why: main requires item id for item in listing equals model a model b to be true, so a false result stops the invalid state.
                    assert {item["id"] for item in listing["data"]} == {"model-a", "model-b"}
                    # What: leave the readiness loop after a valid listing; why: both expected models are visible and qualification can begin.
                    break
                # What: handle oserror and value error by if time monotonic at least deadline or proc poll; why: main converts that failure into this concrete recovery, response, or cleanup behavior.
                except (OSError, ValueError):
                    # What: gate on deadline and monotonic and poll and time and proc before the computed value; why: main admits the computed value only for this predicate and excludes the opposite state.
                    if time.monotonic() >= deadline or proc.poll() is not None:
                        # What: re-propagate the active failure to the caller; why: main stops this rejected path before it can mutate state, dispatch work, or report success.
                        raise
                    # What: wait half a second before retrying the model-list request; why: readiness polling needs backoff instead of a busy loop.
                    time.sleep(0.5)
            # What: iterate across enumerate to perform started and monotonic and time; why: main repeats the body only while or for the loop header admits an iteration.
            for index, (alias, streaming) in enumerate((("model-a", False), ("model-b", True), ("model-a", True))):
                # What: compute started from monotonic and time; why: row model alias stream streaming seconds later reads started, so main must retain the computed value under that name.
                started = time.monotonic()
                # What: preserve the exact print f trial started index alias flush literal fragment; why: main passes this fragment verbatim through print(f"TRIAL_STARTED {index} {alias}", flush=True), because changing it would alter a protocol payload, serialized fixture, or public message.
                print(f"TRIAL_STARTED {index} {alias}", flush=True)
                # What: compute raw and content from canary and base and alias and streaming; why: artifacts f trial index response write bytes later reads raw and content, so main must retain the computed value under that name.
                raw, content = canary(base, alias, streaming)
                # What: preserve the exact artifacts f trial index response write bytes literal fragment; why: main passes this fragment verbatim through (artifacts / f"trial-{index}.response").write_bytes(raw), because changing it would alter a protocol payload, serialized fixture, or public message.
                (artifacts / f"trial-{index}.response").write_bytes(raw)
                # What: map the model field as alias; why: main sends this field through row so the router selects the canonical model or alias for upstream dispatch.
                row = {"model": alias, "stream": streaming, "seconds": time.monotonic() - started, "content": content, "passed": content == "4"}
                # What: preserve the exact status trials append row literal fragment; why: main passes this fragment verbatim through status["trials"].append(row), because changing it would alter a protocol payload, serialized fixture, or public message.
                status["trials"].append(row)
                # What: checkpoint the completed trial in the result artifact; why: evidence survives if a later trial or cleanup step fails.
                save()
                # What: preserve the exact print trial result json dumps row flush literal fragment; why: main passes this fragment verbatim through print("TRIAL_RESULT " + json.dumps(row), flush=True), because changing it would alter a protocol payload, serialized fixture, or public message.
                print("TRIAL_RESULT " + json.dumps(row), flush=True)
                # What: gate on row before runtime error; why: main admits runtime error only for this predicate and excludes the opposite state.
                if not row["passed"]:
                    # What: raise RuntimeError for the caller; why:  main stops this rejected path before it can mutate state, dispatch work, or report success.
                    raise RuntimeError("deterministic quality gate failed")
            # What: gate on cancellation and args before raw and cancellation and cancellation canary and base; why: main admits raw and cancellation and cancellation canary and base only for this predicate and excludes the opposite state.
            if args.cancellation:
                # What: compute raw and cancellation from cancellation canary and base and model a; why: artifacts cancelled prefix sse write bytes raw later reads raw and cancellation, so main must retain the computed value under that name.
                raw, cancellation = cancellation_canary(base, "model-a")
                # What: preserve the exact artifacts cancelled prefix sse write bytes raw literal fragment; why: main passes this fragment verbatim through (artifacts / "cancelled-prefix.sse").write_bytes(raw), because changing it would alter a protocol payload, serialized fixture, or public message.
                (artifacts / "cancelled-prefix.sse").write_bytes(raw)
                # What: compute status entry from cancellation; why: status cancellation recovery passed later reads status entry, so main must retain the computed value under that name.
                status["cancellation"] = cancellation
                # What: checkpoint the cancellation result before recovery trials; why: disconnect evidence survives if post-cancellation validation fails.
                save()
                # What: iterate across enumerate to perform raw and content and canary and base and alias; why: main repeats the body only while or for the loop header admits an iteration.
                for index, alias in enumerate(("model-a", "model-b", "model-a")):
                    # What: compute raw and content from canary and base and alias and true; why: artifacts f after cancel index alias sse later reads raw and content, so main must retain the computed value under that name.
                    raw, content = canary(base, alias, True)
                    # What: preserve the exact artifacts f after cancel index alias sse literal fragment; why: main passes this fragment verbatim through (artifacts / f"after-cancel-{index}-{alias}.sse").write_bytes(raw), because changing it would alter a protocol payload, serialized fixture, or public message.
                    (artifacts / f"after-cancel-{index}-{alias}.sse").write_bytes(raw)
                    # What: assert that content equals 4; why:  main requires content equals 4 to be true, so a false result stops the invalid state.
                    assert content == "4", "post-cancellation routing failed"
                # What: compute status entry from true; why: status concurrent passed later reads status entry, so main must retain the computed value under that name.
                status["cancellationRecoveryPassed"] = True
                # What: preserve the exact print cancellation recovery ok flush literal fragment; why: main passes this fragment verbatim through print("CANCELLATION_RECOVERY_OK", flush=True), because changing it would alter a protocol payload, serialized fixture, or public message.
                print("CANCELLATION_RECOVERY_OK", flush=True)
            # What: gate on extended and args before names and clients and futures and print and thread pool executor; why: main admits names and clients and futures and print and thread pool executor only for this predicate and excludes the opposite state.
            if args.extended:
                # What: iterate across the computed value to perform clients and futures and thread pool executor and index and future; why: main repeats the body only while or for the loop header admits an iteration.
                for names in (("model-a", "model-a"), ("model-a", "model-b")):
                    # What: enter the ThreadPoolExecutor managed context before futures clients submit canary base name for; why: main releases this resource or lock after futures clients submit canary base name for on both success and failure paths.
                    with ThreadPoolExecutor(2) as clients:
                        # What: compute futures from submit and canary and base and name; why: for index future in enumerate futures later reads futures, so main must retain the computed value under that name.
                        futures = [clients.submit(canary, base, name, True) for name in names]
                        # What: iterate across enumerate and futures to perform raw and content and result and future; why: main repeats the body only while or for the loop header admits an iteration.
                        for index, future in enumerate(futures):
                            # What: compute raw and content from result and future; why: artifacts f concurrent join names index later reads raw and content, so main must retain the computed value under that name.
                            raw, content = future.result()
                            # What: preserve the exact artifacts f concurrent join names index literal fragment; why: main passes this fragment verbatim through (artifacts / f"concurrent-{'-'.join(names)}-{index}.sse").write_bytes(ra, because changing it would alter a protocol payload, serialized fixture, or public me.
                            (artifacts / f"concurrent-{'-'.join(names)}-{index}.sse").write_bytes(raw)
                            # What: assert that content equals 4; why:  main requires content equals 4 to be true, so a false result stops the invalid state.
                            assert content == "4", "concurrent quality gate failed"
                            # What: assert that b usage is present in raw; why: main requires b usage is present in raw to be true, so a false result stops the invalid state.
                            assert b'"usage"' in raw, "streamed usage block missing"
                    # What: preserve the exact print concurrent ok join names flush literal fragment; why: main passes this fragment verbatim through print("CONCURRENT_OK " + ",".join(names), flush=True), because changing it would alter a protocol payload, serialized fixture, or public message.
                    print("CONCURRENT_OK " + ",".join(names), flush=True)
                # What: compute status entry from true; why: status idle eviction passed later reads status entry, so main must retain the computed value under that name.
                status["concurrentPassed"] = True
                # What: compute deadline from monotonic and time and 30; why: while time monotonic deadline later reads deadline, so main must retain the computed value under that name.
                deadline = time.monotonic() + 30
                # What: iterate across deadline and monotonic and time to perform running and loads and json and http and base; why: main repeats the body only while or for the loop header admits an iteration.
                while time.monotonic() < deadline:
                    # What: compute running from loads and json and http and base and running; why: if running get running later reads running, so main must retain the computed value under that name.
                    running = json.loads(http(base + "/running"))
                    # What: gate on get and running before status; why: main admits status only for this predicate and excludes the opposite state.
                    if running.get("running") == []:
                        # What: compute status entry from true; why: assert status get idle eviction passed idle ttl did later reads status entry, so main must retain the computed value under that name.
                        status["idleEvictionPassed"] = True
                        # What: leave the idle-eviction loop after unload; why: the engine is no longer running and the eviction gate is satisfied.
                        break
                    # What: pause one second before checking idle eviction again; why: the qualifier gives asynchronous unload work time to complete without busy-waiting.
                    time.sleep(1)
                # What: assert that status get idle eviction passed; why: main requires status get idle eviction passed to be true, so a false result stops the invalid state.
                assert status.get("idleEvictionPassed"), "idle TTL did not unload the models"
                # What: preserve the exact print idle eviction ok flush literal fragment; why: main passes this fragment verbatim through print("IDLE_EVICTION_OK", flush=True), because changing it would alter a protocol payload, serialized fixture, or public message.
                print("IDLE_EVICTION_OK", flush=True)
    # What: handle base exception by status error repr exc; why: main converts that failure into this concrete recovery, response, or cleanup behavior.
    except BaseException as exc:
        # What: compute status entry from repr and exc; why: status cleanup error repr exc later reads status entry, so main must retain the computed value under that name.
        status["error"] = repr(exc)
        # What: preserve the exact print qualification failed repr exc flush literal fragment; why: main passes this fragment verbatim through print("QUALIFICATION_FAILED " + repr(exc), flush=True), because changing it would alter a protocol payload, serialized fixture, or public message.
        print("QUALIFICATION_FAILED " + repr(exc), flush=True)
    # What: run if proc is not on every exit path; why: main performs this cleanup after success, rejection, or exception so resources and accounting cannot remain stranded.
    finally:
        # What: gate on proc before oserror and timeout expired and poll and killpg and pid; why: main admits oserror and timeout expired and poll and killpg and pid only for this predicate and excludes the opposite state.
        if proc is not None:
            # What: establish the handler boundary for the protected operation; why: main routes failures to oserror and timeout expired and subprocess while preserving cleanup and success flow.
            try:
                # What: gate on poll and proc before killpg and pid and sigterm and os and proc; why: main admits killpg and pid and sigterm and os and proc only for this predicate and excludes the opposite state.
                if proc.poll() is None:
                    # What: call os.killpg with pid and proc and sigterm and signal; why: main invokes os.killpg while performing try; the call advances that operation through its result or side effect.
                    os.killpg(proc.pid, signal.SIGTERM)
                    # What: establish the handler boundary for the protected operation; why: main routes failures to timeout expired and subprocess while preserving cleanup and success flow.
                    try:
                        # What: supply timeout to proc.wait; why: main binds this 60 value to proc.wait's timeout input.
                        proc.wait(timeout=60)
                    # What: handle timeout expired and subprocess by os killpg proc pid signal sigkill; why: main converts that failure into this concrete recovery, response, or cleanup behavior.
                    except subprocess.TimeoutExpired:
                        # What: call os.killpg with pid and proc and sigkill and signal; why: main invokes os.killpg while performing proc wait timeout; the call advances that operation through its result or side effect.
                        os.killpg(proc.pid, signal.SIGKILL)
                        # What: supply timeout to proc.wait; why: main binds this 10 value to proc.wait's timeout input.
                        proc.wait(timeout=10)
            # What: handle oserror and timeout expired and subprocess by status cleanup error repr exc; why: main converts that failure into this concrete recovery, response, or cleanup behavior.
            except (OSError, subprocess.TimeoutExpired) as exc:
                # What: compute status entry from repr and exc; why: status restored health wait health args protected url health later reads status entry, so main must retain the computed value under that name.
                status["cleanupError"] = repr(exc)
        # What: gate on maintenance before exception and run and status and wait health and raw; why: main admits exception and run and status and wait health and raw only for this predicate and excludes the opposite state.
        if maintenance:
            # What: establish the handler boundary for the protected operation; why: main routes failures to exception while preserving cleanup and success flow.
            try:
                # What: execute subprocess run service start args protected service check True timeout 180; why: the enclosing symbol requires this operation for its concrete qualification or routing path.
                subprocess.run(service + ["start", args.protected_service], check=True, timeout=180)
                # What: compute status entry from wait health and protected url and args and 300 and health; why: status restored content later reads status entry, so main must retain the computed value under that name.
                status["restoredHealth"] = wait_health(args.protected_url + "/health", 300)
                # What: evaluate and capture raw content canary args protected url protected model; why: the enclosing qualifier uses the captured result in its next validation or artifact step.
                raw, content = canary(args.protected_url, protected_model)
                # What: execute artifacts restored json write bytes raw; why: the enclosing symbol requires this operation for its concrete qualification or routing path.
                (artifacts / "restored.json").write_bytes(raw)
                # What: compute status entry from content and 4; why: print restored str status restored flush later reads status entry, so main must retain the computed value under that name.
                status["restored"] = content == "4"
                # What: execute print RESTORED str status restored flush True; why: the enclosing symbol requires this operation for its concrete qualification or routing path.
                print("RESTORED " + str(status["restored"]), flush=True)
            # What: handle exception by status restore error repr exc; why: main converts that failure into this concrete recovery, response, or cleanup behavior.
            except Exception as exc:
                # What: compute status entry from repr and exc; why: passed status restored and error not later reads status entry, so main must retain the computed value under that name.
                status["restoreError"] = repr(exc)
                # What: preserve the exact print restore failed repr exc flush literal fragment; why: main passes this fragment verbatim through print("RESTORE_FAILED " + repr(exc), flush=True), because changing it would alter a protocol payload, serialized fixture, or public message.
                print("RESTORE_FAILED " + repr(exc), flush=True)
        # What: checkpoint the final restoration state; why: the artifact records cleanup success or failure before exit status is computed.
        save()
    # What: compute passed from status and all and len and x and restored; why: and len status trials and all later reads passed, so main must retain the computed value under that name.
    passed = (status["restored"] and "error" not in status and "cleanupError" not in status
              # What: call all with x and status and passed and trials; why: main invokes all while performing if args extended; the call advances that operation through its result or side effect.
              and len(status["trials"]) == 3 and all(x["passed"] for x in status["trials"]))
    # What: gate on extended and args before passed and get and status; why: main admits passed and get and status only for this predicate and excludes the opposite state.
    if args.extended:
        # What: compute passed from passed and get and status and concurrent passed and idle eviction passed; why: passed passed and status get cancellation get later reads passed, so main must retain the computed value under that name.
        passed = passed and status.get("concurrentPassed") and status.get("idleEvictionPassed")
    # What: gate on cancellation and args before passed and get and status; why: main admits passed and get and status only for this predicate and excludes the opposite state.
    if args.cancellation:
        # What: compute passed from passed and get and status and passed and cancellation recovery passed; why: return if passed else later reads passed, so main must retain the computed value under that name.
        passed = passed and status.get("cancellation", {}).get("passed") and status.get("cancellationRecoveryPassed")
    # What: return passed and 0 and 1 from main; why: main exposes passed and 0 and 1 so its caller can continue with the function\'s computed outcome.
    return 0 if passed else 1


# What: gate on name before exit and sys and main; why: qualify admits exit and sys and main only for this predicate and excludes the opposite state.
if __name__ == "__main__":
    # What: call sys.exit with main; why: qualify invokes sys.exit while performing the enclosing return; the call advances that operation through its result or side effect.
    sys.exit(main())
