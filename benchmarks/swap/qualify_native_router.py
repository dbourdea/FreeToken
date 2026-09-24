"""Opt-in native freetoken-swap routing benchmark for an approved Linux window.

It keeps raw requests, responses, daemon logs, catalog paths, and host details
inside a newly created private artifact directory.  It never changes protected
service enablement or configuration, and always attempts restoration after a
maintenance stop.  This is evidence collection, not a production launcher.
"""
# What: document opt in native freetoken swap routing benchmark for in the qualify_native_router docstring; why: introspection and maintainers read this exact docstring fragment to understand qualify native router behavior without executing it.
# What: document it keeps raw requests responses daemon in the qualify_native_router docstring; why: introspection and maintainers read this exact docstring fragment to understand qualify native router behavior without executing it.
# What: document inside a newly created private artifact in the qualify_native_router docstring; why: introspection and maintainers read this exact docstring fragment to understand qualify native router behavior without executing it.
# What: document service enablement or configuration and always in the qualify_native_router docstring; why: introspection and maintainers read this exact docstring fragment to understand qualify native router behavior without executing it.
# What: document maintenance stop this is evidence collection in the qualify_native_router docstring; why: introspection and maintainers read this exact docstring fragment to understand qualify native router behavior without executing it.
# What: preserve the paragraph boundary in the the qualify_native_router docstring; why: introspection and maintainers read this paragraph break to understand qualify native router behavior without executing it.

# What: enable postponed evaluation of annotations; why: type hints in qualify_native_router can reference runtime types without eager imports or forward-reference failures.
from __future__ import annotations

# What: import argparse for main using argparse; why: main uses argparse argument parser, making that imported dependency available to its named operation.
import argparse

# What: import base64 for control plane canary using base64; why: control_plane_canary uses base64 b64encode, making that imported dependency available to its named operation.
import base64

# What: import json for request json using json; why: request_json uses json loads, making that imported dependency available to its named operation.
import json

# What: import os for stop process group using os; why: stop_process_group uses os killpg, making that imported dependency available to its named operation.
import os

# What: import secrets for main using secrets; why: main uses secrets token urlsafe, making that imported dependency available to its named operation.
import secrets

# What: import signal for stop process group using signal; why: stop_process_group uses signal sigterm, making that imported dependency available to its named operation.
import signal

# What: import socket for require expected hostname using socket; why: require_expected_hostname uses socket gethostname, making that imported dependency available to its named operation.
import socket

# What: import subprocess for stop process group using subprocess; why: stop_process_group uses subprocess timeout expired, making that imported dependency available to its named operation.
import subprocess

# What: import sys for main using sys; why: main uses sys platform startswith, making that imported dependency available to its named operation.
import sys

# What: import threading for concurrent canaries using threading; why: concurrent_canaries uses threading lock, making that imported dependency available to its named operation.
import threading

# What: import time for canary using time; why: canary uses time monotonic, making that imported dependency available to its named operation.
import time

# What: import urllib error for request json using urllib and error; why: request_json uses urllib request request, making that imported dependency available to its named operation.
import urllib.error

# What: import urllib request for request json using urllib and request; why: request_json uses urllib request request, making that imported dependency available to its named operation.
import urllib.request

# What: import path for upstream model rewrite canary using pathlib and path; why: upstream_model_rewrite_canary uses the path annotation in upstream model rewrite canary, making that imported dependency available to its named operation.
from pathlib import Path

# What: compute native auth base from the named fixture input; why: global native auth base native api key later reads native auth base, so qualify_native_router must retain the computed value under that name.
_NATIVE_AUTH_BASE: str | None = None
# What: compute native api key from the named fixture input; why: global native auth base native api key later reads native api key, so qualify_native_router must retain the computed value under that name.
_NATIVE_API_KEY: str | None = None


# What: define require_expected_hostname and its declared inputs; why: callers use require_expected_hostname to perform the behavior named by this helper without duplicating its boundary checks.
def require_expected_hostname(expected: str, *, actual: str | None = None) -> str:
    """Require an exact operator-supplied host without disclosing either name."""
    # What: document require an exact operator supplied host without in the require_expected_hostname docstring; why: introspection and maintainers read this exact docstring fragment to understand require expected hostname behavior without executing it.
    # What: evaluate and capture actual socket gethostname if actual is None else actual; why: the enclosing qualifier uses the captured result in its next validation or artifact step.
    actual = socket.gethostname() if actual is None else actual
    # What: gate on expected and actual before runtime error; why: require_expected_hostname admits runtime error only for this predicate and excludes the opposite state.
    if not expected or "\x00" in expected or actual != expected:
        # What: raise RuntimeError for the caller; why: require_expected_hostname stops this rejected path before it can mutate state, dispatch work, or report success.
        raise RuntimeError(
            # What: execute qualification host does not match the operator supplied expected hostname; why: the enclosing symbol requires this operation for its concrete qualification or routing path.
            "qualification host does not match the operator-supplied expected hostname"
        # What: complete the RuntimeError call with ordered positional inputs; why: require_expected_hostname groups the supplied clauses as one RuntimeError call before its value is consumed.
        )
    # What: return actual from require_expected_hostname; why: require_expected_hostname exposes actual so its caller can continue with the function\'s computed outcome.
    return actual


# What: define the protected service command selector; why: qualification must restore either a system or user-owned workload through its real manager.
def protected_service_command(scope: str) -> list[str]:
    # What: select the system service manager; why: existing qualification callers retain their passwordless sudo behavior by default.
    if scope == "system":
        # What: return the non-interactive systemctl prefix; why: maintenance must never block waiting for a password prompt.
        return ["sudo", "-n", "systemctl"]
    # What: select the invoking user's service manager; why: LAN-215 protects Nemotron with a user-scoped unit.
    if scope == "user":
        # What: return the user systemctl prefix; why: stopping the wrong system scope would fail restoration or touch unrelated services.
        return ["systemctl", "--user"]
    # What: reject unrecognized service scope; why: lifecycle ownership must be explicit before any maintenance mutation.
    raise ValueError("protected service scope must be 'system' or 'user'")


# What: define configure_native_auth around base and api key; why: its direct callers call configure_native_auth for configure native auth and rely on this exact input and result contract.
def configure_native_auth(base: str, api_key: str) -> None:
    """Scope private router credentials to the exact temporary daemon origin."""
    # What: document scope private router credentials to the in the configure_native_auth docstring; why: introspection and maintainers read this exact docstring fragment to understand configure native auth behavior without executing it.
    # What: apply the global native auth base native api key portion of the enclosing predicate; why: this clause remains in configure_native_auth\'s enclosing expression so its grouping and evaluation order stay intact.
    global _NATIVE_AUTH_BASE, _NATIVE_API_KEY
    # What: compute native auth base from rstrip and base and value; why: the enclosing return or state update later reads native auth base, so configure_native_auth must retain the computed value under that name.
    _NATIVE_AUTH_BASE = base.rstrip("/")
    # What: compute native api key from api key; why: the enclosing return or state update later reads native api key, so configure_native_auth must retain the computed value under that name.
    _NATIVE_API_KEY = api_key


# What: define _native_headers around url; why: its direct callers call _native_headers for native headers and rely on this exact input and result contract.
def _native_headers(url: str) -> dict[str, str]:
    # What: gate on native auth base and native api key and url and startswith before native api key; why: _native_headers admits native api key only for this predicate and excludes the opposite state.
    if (
        # What: apply the native auth base is not portion of the enclosing predicate; why: this clause remains in _native_headers\'s enclosing expression so its grouping and evaluation order stay intact.
        _NATIVE_AUTH_BASE is not None
        # What: apply the and native api key is not portion of the enclosing predicate; why: this clause remains in _native_headers\'s enclosing expression so its grouping and evaluation order stay intact.
        and _NATIVE_API_KEY is not None
        # What: call url.startswith with native auth base and value; why: _native_headers consumes the url.startswith return value while evaluating and (url == _NATIVE_AUTH_BASE or url.startswith(_NATIVE_AUTH_BASE + "/").
        and (url == _NATIVE_AUTH_BASE or url.startswith(_NATIVE_AUTH_BASE + "/"))
    # What: complete the enclosing predicate with if native auth base is not and native api key is not and; why: _native_headers groups the supplied clauses as one enclosing predicate expression before its value is consumed.
    ):
        # What: map the authorization field as native api key and bearer; why: _native_headers carries authorization into return {"Authorization": f"Bearer {_NATIVE_API_KEY}"}.
        return {"Authorization": f"Bearer {_NATIVE_API_KEY}"}
    # What: return no value from _native_headers; why: _native_headers returns no value to callers that depend on its completed result.
    return {}


# What: define request_json around url and body and timeout and method; why: its direct callers call request_json for request json and rely on this exact input and result contract.
def request_json(
    # What: declare the url input for request_json; why: request_json consumes url during url, so callers must bind it with the other signature inputs.
    url: str,
    # What: declare the body input for request_json; why: request_json consumes body during data if body is else json dumps, so callers must bind it with the other signature inputs.
    body: dict | None = None,
    # What: mark the remaining parameters as keyword-only; why: request_json prevents callers from confusing adjacent lifecycle and timing arguments.
    *,
    # What: declare the timeout input for request_json; why: request_json consumes timeout during with urllib request urlopen request timeout timeout as, so callers must bind it with the other signature inputs.
    timeout: float = 30,
    # What: declare the method input for request_json; why: request_json consumes method during method method, so callers must bind it with the other signature inputs.
    method: str | None = None,
# What: complete the enclosing predicate collection with bytes and dict; why: request_json groups the supplied clauses as one enclosing predicate collection collection before its value is consumed.
) -> tuple[bytes, dict]:
    # What: compute data from body and encode and dumps and json and utf 8; why: data data later reads data, so request_json must retain the computed value under that name.
    data = None if body is None else json.dumps(body).encode("utf-8")
    # What: begin with origin-scoped authentication headers; why: read-only GET requests must not falsely declare an absent body as JSON.
    headers = _native_headers(url)
    # What: gate the JSON content type on an actual serialized body; why: the router correctly rejects empty requests that claim to contain JSON.
    if data is not None:
        # What: add the JSON media type while preserving authentication; why: body-bearing management requests still require explicit and valid content metadata.
        headers = {"Content-Type": "application/json", **headers}
    # What: compute request from request and url and request and data; why: with urllib request urlopen request timeout timeout as later reads request, so request_json must retain the computed value under that name.
    request = urllib.request.Request(
        # What: apply the url portion of request; why: request_json uses this clause to evaluate request as one grouped value.
        url,
        # What: supply data to urllib.request.Request; why: request_json binds this data value to urllib.request.Request's data input.
        data=data,
        # What: supply the body-aware headers; why: request_json must authenticate every native request without mislabeling empty GET requests as JSON payloads.
        headers=headers,
        # What: supply method to urllib.request.Request; why: request_json binds this method value to urllib.request.Request's method input.
        method=method,
    # What: complete the urllib.request.Request call with data and headers and method; why: request_json groups the supplied clauses as one urllib.request.Request call before its value is consumed.
    )
    # What: enter the urllib.request.urlopen managed context before raw response read; why: request_json releases this resource or lock after raw response read on both success and failure paths.
    with urllib.request.urlopen(request, timeout=timeout) as response:
        # What: compute raw from read and response; why: return raw json loads raw later reads raw, so request_json must retain the computed value under that name.
        raw = response.read()
    # What: return raw and loads and json from request_json; why: request_json exposes raw and loads and json so its caller can continue with the function\'s computed outcome.
    return raw, json.loads(raw)


# What: define request_bytes around url and timeout; why: its direct callers call request_bytes for request bytes and rely on this exact input and result contract.
def request_bytes(url: str, *, timeout: float = 30) -> bytes:
    # What: compute request from request and url and request and urllib; why: with urllib request urlopen request timeout timeout as later reads request, so request_bytes must retain the computed value under that name.
    request = urllib.request.Request(url, headers=_native_headers(url))
    # What: enter the urllib.request.urlopen managed context before return response read; why: request_bytes releases this resource or lock after return response read on both success and failure paths.
    with urllib.request.urlopen(request, timeout=timeout) as response:
        # What: return read and response from request_bytes; why: request_bytes exposes read and response so its caller can continue with the function\'s computed outcome.
        return response.read()


# What: define wait_json around url and seconds; why: its direct callers call wait_json for wait json and rely on this exact input and result contract.
def wait_json(url: str, *, seconds: float) -> dict:
    # What: compute deadline from seconds and monotonic and time; why: while time monotonic deadline later reads deadline, so wait_json must retain the computed value under that name.
    deadline = time.monotonic() + seconds
    # What: compute last from the named fixture input; why: last exc later reads last, so wait_json must retain the computed value under that name.
    last: Exception | None = None
    # What: iterate across deadline and monotonic and time to perform oserror and value error and httperror and last and exc; why: wait_json repeats the body only while or for the loop header admits an iteration.
    while time.monotonic() < deadline:
        # What: establish the handler boundary for the protected operation; why: wait_json routes failures to oserror and value error and httperror and error and urllib while preserving cleanup and success flow.
        try:
            # What: return request json and url and 1 and 3 from wait_json; why: wait_json exposes request json and url and 1 and 3 so its caller can continue with the function\'s computed outcome.
            return request_json(url, timeout=3)[1]
        # What: handle oserror and value error and httperror and error and urllib by last exc; why: wait_json converts that failure into this concrete recovery, response, or cleanup behavior.
        except (OSError, ValueError, urllib.error.HTTPError) as exc:
            # What: compute last from exc; why: raise timeout error f endpoint did not later reads last, so wait_json must retain the computed value under that name.
            last = exc
            # What: call time.sleep with 0 25; why: wait_json invokes time.sleep while performing raise timeout error f endpoint did not; the call advances that operation through its result or side effect.
            time.sleep(0.25)
    # What: raise TimeoutError for the caller; why: wait_json stops this rejected path before it can mutate state, dispatch work, or report success.
    raise TimeoutError(f"endpoint did not become available: {last!r}")


# What: define canary around url and model and direct; why: its direct callers call canary for canary and rely on this exact input and result contract.
def canary(url: str, model: str, *, direct: bool) -> tuple[bytes, dict]:
    """Make one deterministic request and retain raw bytes only in private artifacts."""
    # What: document make one deterministic request and retain in the canary docstring; why: introspection and maintainers read this exact docstring fragment to understand canary behavior without executing it.
    # What: compute body from model and model and messages and temperature and max tokens; why: data json dumps body encode utf 8 later reads body, so canary must retain the computed value under that name.
    body = {
        # What: map the model field as model; why: canary sends this field through body so the router selects the canonical model or alias for upstream dispatch.
        "model": model,
        # What: map the role field as user; why: canary carries role through body into data json dumps body encode utf 8.
        "messages": [{"role": "user", "content": "What is 2 + 2? Reply with only the single digit."}],
        # What: map the temperature field as 0; why: canary carries temperature through body into data json dumps body encode utf 8.
        "temperature": 0,
        # What: map the maximum completion budget as 128 tokens; why: always-on reasoning models need enough bounded space to emit a final deterministic answer after their private analysis.
        "max_tokens": 128,
        # What: map the stream field as true; why: canary carries stream through body into data json dumps body encode utf 8.
        "stream": True,
        # What: map the include usage field as true; why: canary carries include usage through body into data json dumps body encode utf 8.
        "stream_options": {"include_usage": True},
        # What: disable optional thinking while selecting low effort for always-on Harmony models; why: one bounded payload must render correctly for both Qwen-style toggles and gpt-oss's graded reasoning template.
        "chat_template_kwargs": {"enable_thinking": False, "reasoning_effort": "low"},
    # What: complete the body mapping with model and messages and temperature and max tokens and stream; why: canary groups the supplied clauses as one body mapping before its value is consumed.
    }
    # What: compute request from request and request and url and urllib; why: with urllib request urlopen request timeout as response later reads request, so canary must retain the computed value under that name.
    request = urllib.request.Request(
        # What: apply the url v1 chat completions portion of request; why: canary uses this clause to evaluate request as one grouped value.
        url + "/v1/chat/completions",
        # What: supply data to operation.encode; why: canary binds this encode and dumps and body and json and utf 8 value to operation.encode's data input.
        data=json.dumps(body).encode("utf-8"),
        # What: map the content type field as application and json; why: canary carries content type through request into with urllib request urlopen request timeout 660 as response.
        headers={"Content-Type": "application/json", **_native_headers(url)},
    # What: complete the urllib.request.Request call with data and headers; why: canary groups the supplied clauses as one urllib.request.Request call before its value is consumed.
    )
    # What: compute raw from bytearray; why: raw extend chunk later reads raw, so canary must retain the computed value under that name.
    raw = bytearray()
    # What: initialize content as an empty runtime accumulator; why: canary appends or maps entries into it during value choice get delta get content or before consuming the aggregate.
    content: list[str] = []
    # What: compute started from monotonic and time; why: observed s time monotonic started later reads started, so canary must retain the computed value under that name.
    started = time.monotonic()
    # What: compute first byte s from the named fixture input; why: if first byte s is later reads first byte s, so canary must retain the computed value under that name.
    first_byte_s: float | None = None
    # What: compute first token s from the named fixture input; why: if value and first token s is later reads first token s, so canary must retain the computed value under that name.
    first_token_s: float | None = None
    # What: compute completion tokens from the named fixture input; why: if isinstance usage dict and isinstance later reads completion tokens, so canary must retain the computed value under that name.
    completion_tokens: int | None = None
    # What: compute response models from set; why: response models add response model later reads response models, so canary must retain the computed value under that name.
    response_models: set[str] = set()
    # What: attempt the bounded HTTP request before streaming its body; why: an error response must be captured privately instead of being reduced to an opaque status code.
    try:
        # What: open the candidate endpoint with the existing timeout; why: successful responses still use the same bounded network contract.
        response_context = urllib.request.urlopen(request, timeout=660)
    # What: catch an HTTP protocol failure from the candidate; why: qualification needs the server's precise rejection reason to choose a safe corrective action.
    except urllib.error.HTTPError as exc:
        # What: read and decode the bounded error payload; why: the private exception text should preserve actionable diagnostics without publishing request artifacts.
        error_body = exc.read(64 * 1024).decode("utf-8", errors="replace")
        # What: raise a contextual runtime failure chained to the HTTP error; why: the harness must fail closed while retaining the exact private rejection evidence.
        raise RuntimeError(f"canary HTTP {exc.code}: {error_body}") from exc
    # What: enter the successful response managed context before reading chunks; why: canary releases the network resource on both normal completion and parse failure.
    with response_context as response:
        # What: iterate across response to perform observed s and float; why: canary repeats the body only while or for the loop header admits an iteration.
        for chunk in response:
            # What: compute observed s from the named fixture input; why: observed s time monotonic started later reads observed s, so canary must retain the computed value under that name.
            observed_s: float | None = None
            # What: gate on first byte s before observed s and started and monotonic and time; why: canary admits observed s and started and monotonic and time only for this predicate and excludes the opposite state.
            if first_byte_s is None:
                # What: compute observed s from started and monotonic and time; why: first byte s observed s later reads observed s, so canary must retain the computed value under that name.
                observed_s = time.monotonic() - started
                # What: compute first byte s from observed s; why: if first byte s is or first token s is later reads first byte s, so canary must retain the computed value under that name.
                first_byte_s = observed_s
            # What: call raw.extend with chunk; why: canary invokes raw.extend while performing if len raw; the call advances that operation through its result or side effect.
            raw.extend(chunk)
            # What: gate on len and raw before runtime error; why: canary admits runtime error only for this predicate and excludes the opposite state.
            if len(raw) > 8 * 1024 * 1024:
                # What: raise RuntimeError for the caller; why:  canary stops this rejected path before it can mutate state, dispatch work, or report success.
                raise RuntimeError("canary response exceeded private capture bound")
            # What: gate on startswith and chunk and strip before event and loads and json and chunk; why: canary admits event and loads and json and chunk only for this predicate and excludes the opposite state.
            if chunk.startswith(b"data: ") and chunk.strip() != b"data: [DONE]":
                # What: compute event from loads and json and chunk and 6; why: response model event get model later reads event, so canary must retain the computed value under that name.
                event = json.loads(chunk[6:])
                # What: compute response model from get and event and model; why: if isinstance response model str later reads response model, so canary must retain the computed value under that name.
                response_model = event.get("model")
                # What: gate on isinstance and response model and str before add and response model and response models; why: canary admits add and response model and response models only for this predicate and excludes the opposite state.
                if isinstance(response_model, str):
                    # What: call response_models.add with response model; why: canary invokes response_models.add while performing usage event get usage; the call advances that operation through its result or side effect.
                    response_models.add(response_model)
                # What: compute usage from get and event and usage; why: if isinstance usage dict and isinstance later reads usage, so canary must retain the computed value under that name.
                usage = event.get("usage")
                # What: gate on isinstance and usage and dict and int and get before completion tokens and usage; why: canary admits completion tokens and usage only for this predicate and excludes the opposite state.
                if isinstance(usage, dict) and isinstance(usage.get("completion_tokens"), int):
                    # What: compute completion tokens from usage and completion tokens; why: if not isinstance completion tokens int or later reads completion tokens, so canary must retain the computed value under that name.
                    completion_tokens = usage["completion_tokens"]
                # What: iterate across get and event to perform value and get and choice; why: canary repeats the body only while or for the loop header admits an iteration.
                for choice in event.get("choices", []):
                    # What: compute value from get and choice and value and content and delta; why: if value and first token s is later reads value, so canary must retain the computed value under that name.
                    value = choice.get("delta", {}).get("content") or ""
                    # What: gate on value and first token s before observed s and started and monotonic and time; why: canary admits observed s and started and monotonic and time only for this predicate and excludes the opposite state.
                    if value and first_token_s is None:
                        # What: gate on observed s before observed s and started and monotonic and time; why: canary admits observed s and started and monotonic and time only for this predicate and excludes the opposite state.
                        if observed_s is None:
                            # What: compute observed s from started and monotonic and time; why: first token s observed s later reads observed s, so canary must retain the computed value under that name.
                            observed_s = time.monotonic() - started
                        # What: compute first token s from observed s; why: if first byte s is or first token s is later reads first token s, so canary must retain the computed value under that name.
                        first_token_s = observed_s
                    # What: call content.append with value; why: canary invokes content.append while performing duration s time monotonic started; the call advances that operation through its result or side effect.
                    content.append(value)
    # What: compute duration s from started and monotonic and time; why: if first byte s is or first token s is later reads duration s, so canary must retain the computed value under that name.
    duration_s = time.monotonic() - started
    # What: compute answer from strip and join and content and value; why: if answer later reads answer, so canary must retain the computed value under that name.
    answer = "".join(content).strip()
    # What: gate on raw before runtime error; why: canary admits runtime error only for this predicate and excludes the opposite state.
    if b"data: [DONE]" not in raw:
        # What: raise RuntimeError for the caller; why:  canary stops this rejected path before it can mutate state, dispatch work, or report success.
        raise RuntimeError("SSE completion marker missing")
    # What: gate on answer before runtime error; why: canary admits runtime error only for this predicate and excludes the opposite state.
    if answer != "4":
        # What: raise RuntimeError for the caller; why:  canary stops this rejected path before it can mutate state, dispatch work, or report success.
        raise RuntimeError("deterministic quality gate failed")
    # What: gate on completion tokens and isinstance and int before runtime error; why: canary admits runtime error only for this predicate and excludes the opposite state.
    if not isinstance(completion_tokens, int) or completion_tokens <= 0:
        # What: raise RuntimeError for the caller; why:  canary stops this rejected path before it can mutate state, dispatch work, or report success.
        raise RuntimeError("streamed completion usage missing")
    # What: gate on first byte s and first token s and duration s before runtime error; why: canary admits runtime error only for this predicate and excludes the opposite state.
    if first_byte_s is None or first_token_s is None or duration_s <= first_token_s:
        # What: raise RuntimeError for the caller; why:  canary stops this rejected path before it can mutate state, dispatch work, or report success.
        raise RuntimeError("stream timing did not permit token-throughput measurement")
    # What: compute decode s from duration s and first token s; why: completion tokens per second completion tokens decode s later reads decode s, so canary must retain the computed value under that name.
    decode_s = duration_s - first_token_s
    # What: compute completion tokens per second from completion tokens and decode s; why: completion tokens per second completion tokens per second later reads completion tokens per second, so canary must retain the computed value under that name.
    completion_tokens_per_second = completion_tokens / decode_s
    # What: gate on len and response models before runtime error; why: canary admits runtime error only for this predicate and excludes the opposite state.
    if len(response_models) > 1:
        # What: raise RuntimeError for the caller; why:  canary stops this rejected path before it can mutate state, dispatch work, or report success.
        raise RuntimeError("SSE completion reported inconsistent upstream model names")
    # What: return bytes and raw and model and first byte s from canary; why: canary exposes bytes and raw and model and first byte s so its caller can continue with the function\'s computed outcome.
    return bytes(raw), {
        # What: map the route field as direct and direct and native router; why: canary carries route into "route": "direct" if direct else "native_router".
        "route": "direct" if direct else "native_router",
        # What: map the model field as model; why: canary sends this field through "model": model so the router selects the canonical model or alias for upstream dispatch.
        "model": model,
        # What: map the response model field as next and iter and response models; why: canary carries response model into "responseModel": next(iter(response_models), None).
        "responseModel": next(iter(response_models), None),
        # What: map the first byte seconds field as first byte s; why: canary carries first byte seconds into "firstByteSeconds": first_byte_s.
        "firstByteSeconds": first_byte_s,
        # What: map the first token seconds field as first token s; why: canary carries first token seconds into "firstTokenSeconds": first_token_s.
        "firstTokenSeconds": first_token_s,
        # What: map the duration seconds field as duration s; why: canary carries duration seconds into "durationSeconds": duration_s.
        "durationSeconds": duration_s,
        # What: map the decode seconds field as decode s; why: canary carries decode seconds into "decodeSeconds": decode_s.
        "decodeSeconds": decode_s,
        # What: map the completion tokens field as completion tokens; why: canary carries completion tokens into "completionTokens": completion_tokens.
        "completionTokens": completion_tokens,
        # What: map the completion tokens per second field as completion tokens per second; why: canary carries completion tokens per second into "completionTokensPerSecond": completion_tokens_per_second.
        "completionTokensPerSecond": completion_tokens_per_second,
        # What: map the response bytes field as len and raw; why: canary carries response bytes into "responseBytes": len(raw).
        "responseBytes": len(raw),
        # What: map the passed field as true; why: canary carries passed into "passed": True.
        "passed": True,
    # What: complete the enclosing predicate collection with bytes and raw and model and first byte s and first token s and duration s; why: canary groups the supplied clauses as one enclosing predicate collection collection before its value is consumed.
    }


# What: define upstream_model_rewrite_canary around base and artifacts; why: its direct callers call upstream_model_rewrite_canary for upstream model rewrite canary and rely on this exact input and result contract.
def upstream_model_rewrite_canary(base: str, artifacts: Path) -> dict:
    """Prove an alias is rewritten upstream without changing routing identity."""
    # What: document prove an alias is rewritten upstream in the upstream_model_rewrite_canary docstring; why: introspection and maintainers read this exact docstring fragment to understand upstream model rewrite canary behavior without executing it.
    # What: compute and before from request json and base and router and status; why: value after request json base router status later reads and before, so upstream_model_rewrite_canary must retain the computed value under that name.
    _, before = request_json(base + "/router/status")
    # What: compute prior activations from get and before and activations; why: if before get active profile model a or not later reads prior activations, so upstream_model_rewrite_canary must retain the computed value under that name.
    prior_activations = before.get("activations")
    # What: gate on get and isinstance and prior activations and int and before before runtime error; why: upstream_model_rewrite_canary admits runtime error only for this predicate and excludes the opposite state.
    if before.get("activeProfile") != "model-a" or not isinstance(prior_activations, int):
        # What: raise RuntimeError for the caller; why:  upstream_model_rewrite_canary stops this rejected path before it can mutate state, dispatch work, or report success.
        raise RuntimeError("upstream model rewrite canary requires resident model-a")
    # What: compute raw and completion from canary and base and compat and model a and false; why: artifacts upstream model rewrite sse write bytes raw later reads raw and completion, so upstream_model_rewrite_canary must retain the computed value under that name.
    raw, completion = canary(base, "compat/model-a", direct=False)
    # What: compute and after from request json and base and router and status; why: the enclosing return or state update later reads and after, so upstream_model_rewrite_canary must retain the computed value under that name.
    _, after = request_json(base + "/router/status")
    # What: gate on prior activations and get and completion and after before runtime error; why: upstream_model_rewrite_canary admits runtime error only for this predicate and excludes the opposite state.
    if (
        # What: call completion.get with response model; why: upstream_model_rewrite_canary invokes completion.get while performing or after get active profile model a; the call advances that operation through its result or side effect.
        completion.get("responseModel") != "model-a"
        # What: call after.get with active profile; why: upstream_model_rewrite_canary invokes after.get while performing or after get active requests; the call advances that operation through its result or side effect.
        or after.get("activeProfile") != "model-a"
        # What: call after.get with active requests; why: upstream_model_rewrite_canary invokes after.get while performing or after get activations prior activations; the call advances that operation through its result or side effect.
        or after.get("activeRequests") != 0
        # What: call after.get with activations; why: upstream_model_rewrite_canary consumes the after.get return value while evaluating or after.get("activations") != prior_activations.
        or after.get("activations") != prior_activations
    # What: complete the enclosing predicate with if completion get response model differs from model a or after get active profile; why: upstream_model_rewrite_canary groups the supplied clauses as one enclosing predicate expression before its value is consumed.
    ):
        # What: raise RuntimeError for the caller; why:  upstream_model_rewrite_canary stops this rejected path before it can mutate state, dispatch work, or report success.
        raise RuntimeError("alias was not rewritten upstream with stable routing residency")
    # What: preserve the exact artifacts upstream model rewrite sse write bytes raw literal fragment; why: upstream_model_rewrite_canary passes this fragment verbatim through (artifacts / "upstream-model-rewrite.sse").write_bytes(raw), because changing it would alter a protocol payload, serialized fixture, or public m.
    (artifacts / "upstream-model-rewrite.sse").write_bytes(raw)
    # What: return; why:  the caller consumes this value as the function’s success-path result.
    return {
        # What: map the requested model field as compat and model a; why: upstream_model_rewrite_canary carries requested model into "requestedModel": "compat/model-a".
        "requestedModel": "compat/model-a",
        # What: map the upstream response model field as model a; why: upstream_model_rewrite_canary carries upstream response model into "upstreamResponseModel": "model-a".
        "upstreamResponseModel": "model-a",
        # What: map the resident profile field as model a; why: upstream_model_rewrite_canary carries resident profile into "residentProfile": "model-a".
        "residentProfile": "model-a",
        # What: map the activation delta field as 0; why: upstream_model_rewrite_canary carries activation delta into "activationDelta": 0.
        "activationDelta": 0,
        # What: map the passed field as true; why: upstream_model_rewrite_canary carries passed into "passed": True.
        "passed": True,
    # What: complete the enclosing predicate mapping with requested model and upstream response model and resident profile and activation delta and passed; why: upstream_model_rewrite_canary groups the supplied clauses as one enclosing predicate mapping mapping before its value is consumed.
    }


# What: define validate_loading_feedback around raw and expected; why: its direct callers call validate_loading_feedback for validate loading feedback and rely on this exact input and result contract.
def validate_loading_feedback(raw: bytes, *, expected: bool) -> dict:
    """Require the private SSE capture to match the expected router loading state."""
    # What: document require the private sse capture to in the validate_loading_feedback docstring; why: introspection and maintainers read this exact docstring fragment to understand validate loading feedback behavior without executing it.
    # What: initialize reasoning as an empty runtime accumulator; why: validate_loading_feedback appends or maps entries into it during reasoning append value before consuming the aggregate.
    reasoning: list[str] = []
    # What: iterate across splitlines and raw to perform line and startswith; why: validate_loading_feedback repeats the body only while or for the loop header admits an iteration.
    for line in raw.splitlines():
        # What: gate on line and startswith before the computed value; why: validate_loading_feedback admits the computed value only for this predicate and excludes the opposite state.
        if not line.startswith(b"data: ") or line == b"data: [DONE]":
            # What: apply the continue portion of the enclosing predicate; why: this clause remains in validate_loading_feedback\'s enclosing expression so its grouping and evaluation order stay intact.
            continue
        # What: establish the handler boundary for the protected operation; why: validate_loading_feedback routes failures to unicode decode error and jsondecode error and json while preserving cleanup and success flow.
        try:
            # What: compute event from loads and json and line and 6; why: for choice in event get choices later reads event, so validate_loading_feedback must retain the computed value under that name.
            event = json.loads(line[6:])
        # What: handle unicode decode error and jsondecode error and json by continue; why: validate_loading_feedback converts that failure into this concrete recovery, response, or cleanup behavior.
        except (UnicodeDecodeError, json.JSONDecodeError):
            # What: apply the continue portion of the enclosing predicate; why: this clause remains in validate_loading_feedback\'s enclosing expression so its grouping and evaluation order stay intact.
            continue
        # What: iterate across get and event to perform delta and isinstance and choice and dict and get; why: validate_loading_feedback repeats the body only while or for the loop header admits an iteration.
        for choice in event.get("choices", []):
            # What: compute delta from isinstance and choice and dict and get and delta; why: value delta get reasoning content if isinstance delta later reads delta, so validate_loading_feedback must retain the computed value under that name.
            delta = choice.get("delta", {}) if isinstance(choice, dict) else {}
            # What: compute value from isinstance and delta and dict and get and reasoning content; why: if isinstance value str later reads value, so validate_loading_feedback must retain the computed value under that name.
            value = delta.get("reasoning_content") if isinstance(delta, dict) else None
            # What: gate on isinstance and value and str before append and value and reasoning; why: validate_loading_feedback admits append and value and reasoning only for this predicate and excludes the opposite state.
            if isinstance(value, str):
                # What: call reasoning.append with value; why: validate_loading_feedback invokes reasoning.append while performing combined join reasoning; the call advances that operation through its result or side effect.
                reasoning.append(value)
    # What: compute combined from join and reasoning and value; why: observed freetoken swap loading model in combined later reads combined, so validate_loading_feedback must retain the computed value under that name.
    combined = "".join(reasoning)
    # What: compute observed from combined and freetoken swap and loading and model; why: if observed expected later reads observed, so validate_loading_feedback must retain the computed value under that name.
    observed = "freetoken-swap loading model:" in combined
    # What: gate on observed and expected before state and expected; why: validate_loading_feedback admits state and expected only for this predicate and excludes the opposite state.
    if observed != expected:
        # What: compute state from expected and missing and unexpected; why: raise runtime error f router loading feedback later reads state, so validate_loading_feedback must retain the computed value under that name.
        state = "missing" if expected else "unexpected"
        # What: raise RuntimeError for the caller; why: validate_loading_feedback stops this rejected path before it can mutate state, dispatch work, or report success.
        raise RuntimeError(f"router loading feedback was {state} for this qualification trial")
    # What: map the expected field as expected; why: validate_loading_feedback carries expected into return {"expected": expected, "observed": observed, "passed": True}.
    return {"expected": expected, "observed": observed, "passed": True}


# What: define concurrent_canaries around base and model and seconds; why: its direct callers call concurrent_canaries for concurrent canaries and rely on this exact input and result contract.
def concurrent_canaries(base: str, model: str, *, seconds: float = 180) -> tuple[list[tuple[bytes, dict]], dict]:
    """Run two same-profile streams and prove they did not trigger a model swap."""
    # What: document run two same profile streams and prove in the concurrent_canaries docstring; why: introspection and maintainers read this exact docstring fragment to understand concurrent canaries behavior without executing it.
    # What: compute and before from request json and base and router and status; why: value after request json base router status later reads and before, so concurrent_canaries must retain the computed value under that name.
    _, before = request_json(base + "/router/status")
    # What: compute prior activations from get and before and activations; why: if before get active profile model or not later reads prior activations, so concurrent_canaries must retain the computed value under that name.
    prior_activations = before.get("activations")
    # What: gate on model and get and isinstance and prior activations and int before runtime error; why: concurrent_canaries admits runtime error only for this predicate and excludes the opposite state.
    if before.get("activeProfile") != model or not isinstance(prior_activations, int):
        # What: raise RuntimeError for the caller; why:  concurrent_canaries stops this rejected path before it can mutate state, dispatch work, or report success.
        raise RuntimeError("same-model concurrency requires an already active profile")
    # What: initialize results as an empty runtime accumulator; why: concurrent_canaries appends or maps entries into it during results append value before consuming the aggregate.
    results: list[tuple[bytes, dict]] = []
    # What: initialize errors as an empty runtime accumulator; why: concurrent_canaries appends or maps entries into it during errors append exc before consuming the aggregate.
    errors: list[BaseException] = []
    # What: compute lock from lock and threading; why: with lock later reads lock, so concurrent_canaries must retain the computed value under that name.
    lock = threading.Lock()
    # What: compute gate from barrier and threading and 3; why: gate wait timeout seconds later reads gate, so concurrent_canaries must retain the computed value under that name.
    gate = threading.Barrier(3)

    # What: define run_one around the current object state; why: its direct callers call run_one for run one and rely on this exact input and result contract.
    def run_one() -> None:
        # What: establish the handler boundary for the protected operation; why: run_one routes failures to base exception while preserving cleanup and success flow.
        try:
            # What: supply timeout to gate.wait; why: run_one binds this seconds value to gate.wait's timeout input.
            gate.wait(timeout=seconds)
            # What: compute value from canary and base and model and false; why: results append value later reads value, so run_one must retain the computed value under that name.
            value = canary(base, model, direct=False)
            # What: enter the lock managed context before results append value; why: run_one releases this resource or lock after results append value on both success and failure paths.
            with lock:
                # What: call results.append with value; why: run_one invokes results.append while performing except base exception as exc; the call advances that operation through its result or side effect.
                results.append(value)
        # What: handle base exception by with lock; why: run_one converts that failure into this concrete recovery, response, or cleanup behavior.
        except BaseException as exc:  # noqa: BLE001 -- cleanup must record interrupts as qualification failures.
            # What: enter the lock managed context before errors append exc; why: run_one releases this resource or lock after errors append exc on both success and failure paths.
            with lock:
                # What: call errors.append with exc; why: run_one invokes errors.append while performing the enclosing return; the call advances that operation through its result or side effect.
                errors.append(exc)

    # What: compute workers from thread and index and threading and run one; why: for worker in workers later reads workers, so concurrent_canaries must retain the computed value under that name.
    workers = [threading.Thread(target=run_one, name=f"native-router-concurrent-{index}", daemon=True)
               # What: call range with 2; why: concurrent_canaries invokes range while performing for worker in workers; the call advances that operation through its result or side effect.
               for index in range(2)]
    # What: iterate across workers to perform start and worker; why: concurrent_canaries repeats the body only while or for the loop header admits an iteration.
    for worker in workers:
        # What: call worker.start with the declared inputs; why: concurrent_canaries invokes worker.start while performing gate wait timeout seconds; the call advances that operation through its result or side effect.
        worker.start()
    # What: supply timeout to gate.wait; why: concurrent_canaries binds this seconds value to gate.wait's timeout input.
    gate.wait(timeout=seconds)
    # What: iterate across workers to perform join and seconds and worker; why: concurrent_canaries repeats the body only while or for the loop header admits an iteration.
    for worker in workers:
        # What: call worker.join with seconds; why: concurrent_canaries invokes worker.join while performing if any worker is alive for worker in; the call advances that operation through its result or side effect.
        worker.join(seconds)
    # What: gate on any and is alive and worker and workers before timeout error; why: concurrent_canaries admits timeout error only for this predicate and excludes the opposite state.
    if any(worker.is_alive() for worker in workers):
        # What: raise TimeoutError for the caller; why: concurrent_canaries stops this rejected path before it can mutate state, dispatch work, or report success.
        raise TimeoutError("same-model concurrent streams did not finish")
    # What: gate on errors before runtime error and errors; why: concurrent_canaries admits runtime error and errors only for this predicate and excludes the opposite state.
    if errors:
        # What: raise RuntimeError for the caller; why:  concurrent_canaries stops this rejected path before it can mutate state, dispatch work, or report success.
        raise RuntimeError("same-model concurrent stream failed") from errors[0]
    # What: compute and after from request json and base and router and status; why: or not all row get passed is later reads and after, so concurrent_canaries must retain the computed value under that name.
    _, after = request_json(base + "/router/status")
    # What: gate on model and prior activations and len and results and all before runtime error; why: concurrent_canaries admits runtime error only for this predicate and excludes the opposite state.
    if (
        # What: call len with results; why: concurrent_canaries invokes len while performing or not all row get passed is; the call advances that operation through its result or side effect.
        len(results) != 2
        # What: call all with results and get and value and row and true; why: concurrent_canaries invokes all while performing or after get active requests; the call advances that operation through its result or side effect.
        or not all(row.get("passed") is True for _, row in results)
        # What: call after.get with active requests; why: concurrent_canaries invokes after.get while performing or after get active profile model; the call advances that operation through its result or side effect.
        or after.get("activeRequests") != 0
        # What: call after.get with active profile; why: concurrent_canaries invokes after.get while performing or after get activations prior activations; the call advances that operation through its result or side effect.
        or after.get("activeProfile") != model
        # What: call after.get with activations; why: concurrent_canaries consumes the after.get return value while evaluating or after.get("activations") != prior_activations.
        or after.get("activations") != prior_activations
    # What: complete the enclosing predicate with if len results differs from 2 or not all; why: concurrent_canaries groups the supplied clauses as one enclosing predicate expression before its value is consumed.
    ):
        # What: raise RuntimeError for the caller; why:  concurrent_canaries stops this rejected path before it can mutate state, dispatch work, or report success.
        raise RuntimeError("same-model concurrency changed native routing residency")
    # What: return results and model and route and model and requests from concurrent_canaries; why: concurrent_canaries exposes results and model and route and model and requests so its caller can continue with the function\'s computed outcome.
    return results, {
        # What: map the route field as native router; why: concurrent_canaries carries route into "route": "native_router".
        "route": "native_router",
        # What: map the model field as model; why: concurrent_canaries sends this field through "model": model so the router selects the canonical model or alias for upstream dispatch.
        "model": model,
        # What: map the requests field as 2; why: concurrent_canaries carries requests into "requests": 2.
        "requests": 2,
        # What: map the activation delta field as 0; why: concurrent_canaries carries activation delta into "activationDelta": 0.
        "activationDelta": 0,
        # What: map the active requests after field as 0; why: concurrent_canaries carries active requests after into "activeRequestsAfter": 0.
        "activeRequestsAfter": 0,
        # What: map the passed field as true; why: concurrent_canaries carries passed into "passed": True.
        "passed": True,
    # What: complete the enclosing predicate collection with results and model and route and model and requests and activation delta; why: concurrent_canaries groups the supplied clauses as one enclosing predicate collection collection before its value is consumed.
    }


# What: define cancellation_canary around base and model and seconds; why: its direct callers call cancellation_canary for cancellation canary and rely on this exact input and result contract.
def cancellation_canary(base: str, model: str, *, seconds: float = 90) -> tuple[bytes, dict]:
    """Prove native router cancellation reaches idle without a normal completion credit.

    The raw partial SSE remains a private artifact.  The returned observation is
    deliberately limited to lifecycle counters and timing-safe booleans.
    """
    # What: document prove native router cancellation reaches idle in the cancellation_canary docstring; why: introspection and maintainers read this exact docstring fragment to understand cancellation canary behavior without executing it.
    # What: document the raw partial sse remains a in the cancellation_canary docstring; why: introspection and maintainers read this exact docstring fragment to understand cancellation canary behavior without executing it.
    # What: document deliberately limited to lifecycle counters and in the cancellation_canary docstring; why: introspection and maintainers read this exact docstring fragment to understand cancellation canary behavior without executing it.
    # What: preserve the paragraph boundary in the the cancellation_canary docstring; why: introspection and maintainers read this paragraph break to understand cancellation canary behavior without executing it.
    # What: compute request id from native qualification cancel; why: content type application json x ft request id request id later reads request id, so cancellation_canary must retain the computed value under that name.
    request_id = "native-qualification-cancel"
    # What: compute and before from request json and base and router and status; why: value cancelled request json base f router later reads and before, so cancellation_canary must retain the computed value under that name.
    _, before = request_json(base + "/router/status")
    # What: compute prior cancellations from get and before and cancellations; why: if not isinstance prior cancellations int or later reads prior cancellations, so cancellation_canary must retain the computed value under that name.
    prior_cancellations = before.get("cancellations")
    # What: compute prior terminal from get and before and terminal streams; why: if not isinstance prior cancellations int or later reads prior terminal, so cancellation_canary must retain the computed value under that name.
    prior_terminal = before.get("terminalStreams")
    # What: gate on isinstance and prior cancellations and int and prior terminal before runtime error; why: cancellation_canary admits runtime error only for this predicate and excludes the opposite state.
    if not isinstance(prior_cancellations, int) or not isinstance(prior_terminal, int):
        # What: raise RuntimeError for the caller; why:  cancellation_canary stops this rejected path before it can mutate state, dispatch work, or report success.
        raise RuntimeError("router status lacks cancellation counters")  # noqa: TRY004 -- malformed remote status is an operational failure.
    # What: compute body from model and model and messages and temperature and max tokens; why: base v1 chat completions data json dumps later reads body, so cancellation_canary must retain the computed value under that name.
    body = {
        # What: map the model field as model; why: cancellation_canary sends this field through body so the router selects the canonical model or alias for upstream dispatch.
        "model": model,
        # What: map the role field as user; why: cancellation_canary carries role through body into base v1 chat completions data json dumps body.
        "messages": [{"role": "user", "content": "Count upward slowly and do not stop."}],
        # What: map the temperature field as 0; why: cancellation_canary carries temperature through body into base v1 chat completions data json dumps body.
        "temperature": 0,
        # What: map the max tokens field as 2048; why: cancellation_canary carries max tokens through body into base v1 chat completions data json dumps body.
        "max_tokens": 2048,
        # What: map the stream field as true; why: cancellation_canary carries stream through body into base v1 chat completions data json dumps body.
        "stream": True,
    # What: complete the body mapping with model and messages and temperature and max tokens and stream; why: cancellation_canary groups the supplied clauses as one body mapping before its value is consumed.
    }
    # What: compute request from request and request and base and urllib; why: with urllib request urlopen request timeout seconds as later reads request, so cancellation_canary must retain the computed value under that name.
    request = urllib.request.Request(
        # What: supply data to operation.encode; why: cancellation_canary binds this encode and dumps and body and json and utf 8 value to operation.encode's data input.
        base + "/v1/chat/completions", data=json.dumps(body).encode("utf-8"),
        # What: supply headers to urllib.request.Request; why: cancellation_canary binds this request id and native headers and base and content type and x ft request id value to urllib.request.Request's headers input.
        headers={
            # What: map the content type field as application and json; why: cancellation_canary carries content type through request into with urllib request urlopen request timeout seconds as response.
            "Content-Type": "application/json", "X-FT-Request-ID": request_id,
            # What: call _native_headers with base; why: cancellation_canary consumes the _native_headers return value while evaluating **_native_headers(base).
            **_native_headers(base),
        # What: complete the request mapping with content type and x ft request id; why: cancellation_canary groups the supplied clauses as one request mapping before its value is consumed.
        },
    # What: complete the urllib.request.Request call with data and headers; why: cancellation_canary groups the supplied clauses as one urllib.request.Request call before its value is consumed.
    )
    # What: compute raw from bytearray; why: raw extend chunk later reads raw, so cancellation_canary must retain the computed value under that name.
    raw = bytearray()
    # What: compute first chunk from event and threading; why: first chunk set later reads first chunk, so cancellation_canary must retain the computed value under that name.
    first_chunk = threading.Event()
    # What: compute finished from event and threading; why: finished set later reads finished, so cancellation_canary must retain the computed value under that name.
    finished = threading.Event()
    # What: initialize errors as an empty runtime accumulator; why: cancellation_canary appends or maps entries into it during errors append exc before consuming the aggregate.
    errors: list[BaseException] = []

    # What: define consume around the current object state; why: its direct callers call consume for consume and rely on this exact input and result contract.
    def consume() -> None:
        # What: establish the handler boundary for the protected operation; why: consume routes failures to exception while preserving cleanup and success flow.
        try:
            # What: enter the urllib.request.urlopen managed context before for chunk in response; why: consume releases this resource or lock after for chunk in response on both success and failure paths.
            with urllib.request.urlopen(request, timeout=seconds) as response:
                # What: iterate across response to perform extend and chunk and raw; why: consume repeats the body only while or for the loop header admits an iteration.
                for chunk in response:
                    # What: call raw.extend with chunk; why: consume invokes raw.extend while performing first chunk set; the call advances that operation through its result or side effect.
                    raw.extend(chunk)
                    # What: call first_chunk.set with the declared inputs; why: consume invokes first_chunk.set while performing except exception as exc cancellation may; the call advances that operation through its result or side effect.
                    first_chunk.set()
        # What: handle exception by errors append exc; why: consume converts that failure into this concrete recovery, response, or cleanup behavior.
        except Exception as exc:  # noqa: BLE001 -- cancellation may close a blocking HTTP read
            # What: call errors.append with exc; why: consume invokes errors.append while performing finally; the call advances that operation through its result or side effect.
            errors.append(exc)
        # What: run finished set on every exit path; why: consume performs this cleanup after success, rejection, or exception so resources and accounting cannot remain stranded.
        finally:
            # What: call finished.set with the declared inputs; why: consume invokes finished.set while performing the enclosing return; the call advances that operation through its result or side effect.
            finished.set()

    # What: compute worker from thread and threading and consume and native router cancel and true; why: worker start later reads worker, so cancellation_canary must retain the computed value under that name.
    worker = threading.Thread(target=consume, name="native-router-cancel", daemon=True)
    # What: compute started from monotonic and time; why: duration seconds time monotonic started later reads started, so cancellation_canary must retain the computed value under that name.
    started = time.monotonic()
    # What: call worker.start with the declared inputs; why: cancellation_canary invokes worker.start while performing if not first chunk wait seconds; the call advances that operation through its result or side effect.
    worker.start()
    # What: gate on wait and seconds and first chunk before timeout error; why: cancellation_canary admits timeout error only for this predicate and excludes the opposite state.
    if not first_chunk.wait(seconds):
        # What: raise TimeoutError for the caller; why:  cancellation_canary stops this rejected path before it can mutate state, dispatch work, or report success.
        raise TimeoutError("cancellation stream produced no first chunk")
    # What: compute and cancelled from request json and base and request id and 30 and router; why: the enclosing return or state update later reads and cancelled, so cancellation_canary must retain the computed value under that name.
    _, cancelled = request_json(base + f"/router/requests/{request_id}/cancel", {}, timeout=30)
    # What: map the cancelled field as true; why: cancellation_canary carries cancelled through if cancelled != {"cancelled": True, "id": request_id} into raise runtime error router did not acknowledge the.
    if cancelled != {"cancelled": True, "id": request_id}:
        # What: raise RuntimeError for the caller; why:  cancellation_canary stops this rejected path before it can mutate state, dispatch work, or report success.
        raise RuntimeError("router did not acknowledge the active cancellation request")
    # What: gate on wait and seconds and finished before timeout error; why: cancellation_canary admits timeout error only for this predicate and excludes the opposite state.
    if not finished.wait(seconds):
        # What: raise TimeoutError for the caller; why:  cancellation_canary stops this rejected path before it can mutate state, dispatch work, or report success.
        raise TimeoutError("cancelled stream did not close")
    # What: compute deadline from seconds and monotonic and time; why: while time monotonic deadline later reads deadline, so cancellation_canary must retain the computed value under that name.
    deadline = time.monotonic() + seconds
    # What: compute status from the named fixture input; why: status request json base router status timeout later reads status, so cancellation_canary must retain the computed value under that name.
    status: dict | None = None
    # What: iterate across deadline and monotonic and time to perform status and request json and base; why: cancellation_canary repeats the body only while or for the loop header admits an iteration.
    while time.monotonic() < deadline:
        # What: compute status from request json and base and 1 and router and status; why: if status get active requests later reads status, so cancellation_canary must retain the computed value under that name.
        status = request_json(base + "/router/status", timeout=3)[1]
        # What: gate on get and status before the computed value; why: cancellation_canary admits the computed value only for this predicate and excludes the opposite state.
        if status.get("activeRequests") == 0:
            # What: apply the break portion of the enclosing predicate; why: this clause remains in cancellation_canary\'s enclosing expression so its grouping and evaluation order stay intact.
            break
        # What: call time.sleep with 0 1; why: cancellation_canary invokes time.sleep while performing if status is or status get active requests; the call advances that operation through its result or side effect.
        time.sleep(0.1)
    # What: gate on status and get before timeout error; why: cancellation_canary admits timeout error only for this predicate and excludes the opposite state.
    if status is None or status.get("activeRequests") != 0:
        # What: raise TimeoutError for the caller; why:  cancellation_canary stops this rejected path before it can mutate state, dispatch work, or report success.
        raise TimeoutError("router did not return to idle after cancellation")
    # What: gate on get and prior cancellations and status before runtime error; why: cancellation_canary admits runtime error only for this predicate and excludes the opposite state.
    if status.get("cancellations") != prior_cancellations + 1:
        # What: raise RuntimeError for the caller; why:  cancellation_canary stops this rejected path before it can mutate state, dispatch work, or report success.
        raise RuntimeError("router cancellation counter did not increment")
    # What: gate on prior terminal and get and status before runtime error; why: cancellation_canary admits runtime error only for this predicate and excludes the opposite state.
    if status.get("terminalStreams") != prior_terminal:
        # What: raise RuntimeError for the caller; why:  cancellation_canary stops this rejected path before it can mutate state, dispatch work, or report success.
        raise RuntimeError("cancelled stream was credited as a normal completion")
    # What: gate on raw before runtime error; why: cancellation_canary admits runtime error only for this predicate and excludes the opposite state.
    if b"data: [DONE]" in raw:
        # What: raise RuntimeError for the caller; why:  cancellation_canary stops this rejected path before it can mutate state, dispatch work, or report success.
        raise RuntimeError("cancelled stream reached a normal terminal event")
    # What: return bytes and raw and model and request id from cancellation_canary; why: cancellation_canary exposes bytes and raw and model and request id so its caller can continue with the function\'s computed outcome.
    return bytes(raw), {
        # What: map the route field as native router; why: cancellation_canary carries route into "route": "native_router".
        "route": "native_router",
        # What: map the model field as model; why: cancellation_canary sends this field through "model": model so the router selects the canonical model or alias for upstream dispatch.
        "model": model,
        # What: map the request id field as request id; why: cancellation_canary carries request id into "requestId": request_id.
        "requestId": request_id,
        # What: map the duration seconds field as started and monotonic and time; why: cancellation_canary carries duration seconds into "durationSeconds": time.monotonic() - started.
        "durationSeconds": time.monotonic() - started,
        # What: map the response bytes field as len and raw; why: cancellation_canary carries response bytes into "responseBytes": len(raw).
        "responseBytes": len(raw),
        # What: map the cancellation incremented field as true; why: cancellation_canary carries cancellation incremented into "cancellationIncremented": True.
        "cancellationIncremented": True,
        # What: map the normal completion credited field as false; why: cancellation_canary carries normal completion credited into "normalCompletionCredited": False.
        "normalCompletionCredited": False,
        # What: map the stream read error field as errors and repr and 0; why: cancellation_canary carries stream read error into "streamReadError": repr(errors[0]) if errors else None.
        "streamReadError": repr(errors[0]) if errors else None,
        # What: map the passed field as true; why: cancellation_canary carries passed into "passed": True.
        "passed": True,
    # What: complete the enclosing predicate collection with bytes and raw and model and request id and started and len; why: cancellation_canary groups the supplied clauses as one enclosing predicate collection collection before its value is consumed.
    }


# What: define conflicting_request_canary around base and active model and waiting model and seconds; why: its direct callers call conflicting_request_canary for conflicting request canary and rely on this exact input and result contract.
def conflicting_request_canary(
    # What: declare the base input for conflicting_request_canary; why: conflicting_request_canary consumes base during restored raw restored row canary base active model direct, so callers must bind it with the other signature inputs.
    base: str, active_model: str, waiting_model: str, *, seconds: float = 180
# What: complete the enclosing predicate collection with bytes and bytes and bytes and dict; why: conflicting_request_canary groups the supplied clauses as one enclosing predicate collection collection before its value is consumed.
) -> tuple[bytes, bytes, bytes, dict]:
    """Hold A, prove B queues, cancel A, then complete B and restore A."""
    # What: document hold a prove b queues cancel in the conflicting_request_canary docstring; why: introspection and maintainers read this exact docstring fragment to understand conflicting request canary behavior without executing it.
    # What: compute request id from native qualification conflict; why: content type application json x ft request id request id later reads request id, so conflicting_request_canary must retain the computed value under that name.
    request_id = "native-qualification-conflict"
    # What: compute and before from request json and base and router and status; why: value after waiting request json base router status later reads and before, so conflicting_request_canary must retain the computed value under that name.
    _, before = request_json(base + "/router/status")
    # What: compute prior activations from get and before and activations; why: if before get active profile active model or not later reads prior activations, so conflicting_request_canary must retain the computed value under that name.
    prior_activations = before.get("activations")
    # What: gate on active model and get and isinstance and prior activations and int before runtime error; why: conflicting_request_canary admits runtime error only for this predicate and excludes the opposite state.
    if before.get("activeProfile") != active_model or not isinstance(prior_activations, int):
        # What: raise RuntimeError for the caller; why:  conflicting_request_canary stops this rejected path before it can mutate state, dispatch work, or report success.
        raise RuntimeError("conflicting-request qualification requires active model A")
    # What: compute body from active model and model and messages and temperature and max tokens; why: base v1 chat completions data json dumps later reads body, so conflicting_request_canary must retain the computed value under that name.
    body = {
        # What: map the model field as active model; why: conflicting_request_canary sends this field through body so the router selects the canonical model or alias for upstream dispatch.
        "model": active_model,
        # What: map the role field as user; why: conflicting_request_canary carries role through body into base v1 chat completions data json dumps body.
        "messages": [{"role": "user", "content": "Count upward slowly and do not stop."}],
        # What: map the temperature field as 0; why: conflicting_request_canary carries temperature through body into base v1 chat completions data json dumps body.
        "temperature": 0, "max_tokens": 2048, "stream": True,
    # What: complete the body mapping with model and messages and temperature and max tokens and stream; why: conflicting_request_canary groups the supplied clauses as one body mapping before its value is consumed.
    }
    # What: compute request from request and request and base and urllib; why: with urllib request urlopen request timeout seconds as later reads request, so conflicting_request_canary must retain the computed value under that name.
    request = urllib.request.Request(
        # What: supply data to operation.encode; why: conflicting_request_canary binds this encode and dumps and body and json and utf 8 value to operation.encode's data input.
        base + "/v1/chat/completions", data=json.dumps(body).encode("utf-8"),
        # What: supply headers to urllib.request.Request; why: conflicting_request_canary binds this request id and native headers and base and content type and x ft request id value to urllib.request.Request's headers input.
        headers={
            # What: map the content type field as application and json; why: conflicting_request_canary carries content type through request into with urllib request urlopen request timeout seconds as response.
            "Content-Type": "application/json", "X-FT-Request-ID": request_id,
            # What: call _native_headers with base; why: conflicting_request_canary consumes the _native_headers return value while evaluating **_native_headers(base).
            **_native_headers(base),
        # What: complete the request mapping with content type and x ft request id; why: conflicting_request_canary groups the supplied clauses as one request mapping before its value is consumed.
        },
    # What: complete the urllib.request.Request call with data and headers; why: conflicting_request_canary groups the supplied clauses as one urllib.request.Request call before its value is consumed.
    )
    # What: compute active raw from bytearray; why: active raw extend chunk later reads active raw, so conflicting_request_canary must retain the computed value under that name.
    active_raw = bytearray()
    # What: compute first chunk from event and threading; why: first chunk set later reads first chunk, so conflicting_request_canary must retain the computed value under that name.
    first_chunk = threading.Event()
    # What: compute active finished from event and threading; why: active finished set later reads active finished, so conflicting_request_canary must retain the computed value under that name.
    active_finished = threading.Event()
    # What: initialize waiting result as an empty runtime accumulator; why: conflicting_request_canary appends or maps entries into it during waiting result append canary base waiting model direct false before consuming the aggregate.
    waiting_result: list[tuple[bytes, dict]] = []
    # What: initialize active errors as an empty runtime accumulator; why: conflicting_request_canary appends or maps entries into it during active errors append exc before consuming the aggregate.
    active_errors: list[BaseException] = []
    # What: initialize waiting errors as an empty runtime accumulator; why: conflicting_request_canary appends or maps entries into it during waiting errors append exc before consuming the aggregate.
    waiting_errors: list[BaseException] = []

    # What: define consume_active around the current object state; why: its direct callers call consume_active for consume active and rely on this exact input and result contract.
    def consume_active() -> None:
        # What: establish the handler boundary for the protected operation; why: consume_active routes failures to exception while preserving cleanup and success flow.
        try:
            # What: enter the urllib.request.urlopen managed context before for chunk in response; why: consume_active releases this resource or lock after for chunk in response on both success and failure paths.
            with urllib.request.urlopen(request, timeout=seconds) as response:
                # What: iterate across response to perform extend and chunk and active raw; why: consume_active repeats the body only while or for the loop header admits an iteration.
                for chunk in response:
                    # What: call active_raw.extend with chunk; why: consume_active invokes active_raw.extend while performing first chunk set; the call advances that operation through its result or side effect.
                    active_raw.extend(chunk)
                    # What: call first_chunk.set with the declared inputs; why: consume_active invokes first_chunk.set while performing except exception as exc; the call advances that operation through its result or side effect.
                    first_chunk.set()
        # What: handle exception by active errors append exc; why: consume_active converts that failure into this concrete recovery, response, or cleanup behavior.
        except Exception as exc:  # noqa: BLE001 -- worker failures are returned to the coordinating test thread.
            # What: call active_errors.append with exc; why: consume_active invokes active_errors.append while performing finally; the call advances that operation through its result or side effect.
            active_errors.append(exc)
        # What: run active finished set on every exit path; why: consume_active performs this cleanup after success, rejection, or exception so resources and accounting cannot remain stranded.
        finally:
            # What: call active_finished.set with the declared inputs; why: consume_active invokes active_finished.set while performing the enclosing return; the call advances that operation through its result or side effect.
            active_finished.set()

    # What: define consume_waiting around the current object state; why: its direct callers call consume_waiting for consume waiting and rely on this exact input and result contract.
    def consume_waiting() -> None:
        # What: establish the handler boundary for the protected operation; why: consume_waiting routes failures to base exception while preserving cleanup and success flow.
        try:
            # What: supply direct to waiting_result.append; why: consume_waiting binds this false value to waiting_result.append's direct input.
            waiting_result.append(canary(base, waiting_model, direct=False))
        # What: handle base exception by waiting errors append exc; why: consume_waiting converts that failure into this concrete recovery, response, or cleanup behavior.
        except BaseException as exc:  # noqa: BLE001 -- cleanup must record interrupts as qualification failures.
            # What: call waiting_errors.append with exc; why: consume_waiting invokes waiting_errors.append while performing the enclosing return; the call advances that operation through its result or side effect.
            waiting_errors.append(exc)

    # What: compute active worker from thread and threading and consume active and true; why: active worker start later reads active worker, so conflicting_request_canary must retain the computed value under that name.
    active_worker = threading.Thread(target=consume_active, daemon=True)
    # What: call active_worker.start with the declared inputs; why: conflicting_request_canary invokes active_worker.start while performing if not first chunk wait seconds; the call advances that operation through its result or side effect.
    active_worker.start()
    # What: gate on wait and seconds and first chunk before timeout error; why: conflicting_request_canary admits timeout error only for this predicate and excludes the opposite state.
    if not first_chunk.wait(seconds):
        # What: raise TimeoutError for the caller; why:  conflicting_request_canary stops this rejected path before it can mutate state, dispatch work, or report success.
        raise TimeoutError("active conflicting stream produced no first chunk")
    # What: compute waiting worker from thread and threading and consume waiting and true; why: waiting worker start later reads waiting worker, so conflicting_request_canary must retain the computed value under that name.
    waiting_worker = threading.Thread(target=consume_waiting, daemon=True)
    # What: call waiting_worker.start with the declared inputs; why: conflicting_request_canary invokes waiting_worker.start while performing deadline time monotonic seconds; the call advances that operation through its result or side effect.
    waiting_worker.start()
    # What: compute deadline from seconds and monotonic and time; why: while time monotonic deadline later reads deadline, so conflicting_request_canary must retain the computed value under that name.
    deadline = time.monotonic() + seconds
    # What: compute queued from the named fixture input; why: queued request json base router status timeout later reads queued, so conflicting_request_canary must retain the computed value under that name.
    queued: dict | None = None
    # What: iterate across deadline and monotonic and time to perform queued and request json and base; why: conflicting_request_canary repeats the body only while or for the loop header admits an iteration.
    while time.monotonic() < deadline:
        # What: compute queued from request json and base and 1 and router and status; why: if queued get queued requests later reads queued, so conflicting_request_canary must retain the computed value under that name.
        queued = request_json(base + "/router/status", timeout=3)[1]
        # What: gate on get and queued before the computed value; why: conflicting_request_canary admits the computed value only for this predicate and excludes the opposite state.
        if queued.get("queuedRequests") == 1:
            # What: apply the break portion of the enclosing predicate; why: this clause remains in conflicting_request_canary\'s enclosing expression so its grouping and evaluation order stay intact.
            break
        # What: call time.sleep with 0 1; why: conflicting_request_canary invokes time.sleep while performing if; the call advances that operation through its result or side effect.
        time.sleep(0.1)
    # What: gate on queued and active model and get before runtime error; why: conflicting_request_canary admits runtime error only for this predicate and excludes the opposite state.
    if (
        # What: call queued.get with queued requests; why: conflicting_request_canary invokes queued.get while performing or queued get active profile active model; the call advances that operation through its result or side effect.
        queued is None or queued.get("queuedRequests") != 1
        # What: call queued.get with active profile; why: conflicting_request_canary invokes queued.get while performing or queued get active requests; the call advances that operation through its result or side effect.
        or queued.get("activeProfile") != active_model
        # What: call queued.get with active requests; why: conflicting_request_canary invokes queued.get while performing or queued get active identity matches engine is not; the call advances that operation through its result or side effect.
        or queued.get("activeRequests") != 1
        # What: call queued.get with active identity matches engine; why: conflicting_request_canary consumes the queued.get return value while evaluating or queued.get("activeIdentityMatchesEngine") is not True.
        or queued.get("activeIdentityMatchesEngine") is not True
    # What: complete the enclosing predicate with if queued is or queued get queued requests differs from 1; why: conflicting_request_canary groups the supplied clauses as one enclosing predicate expression before its value is consumed.
    ):
        # What: raise RuntimeError for the caller; why:  conflicting_request_canary stops this rejected path before it can mutate state, dispatch work, or report success.
        raise RuntimeError("waiting model did not queue behind the active stream")
    # What: gate on request id and request json and base before runtime error; why: conflicting_request_canary admits runtime error only for this predicate and excludes the opposite state.
    if request_json(base + f"/router/requests/{request_id}/cancel", {}, timeout=30)[1] != {
        # What: map the cancelled field as true; why: conflicting_request_canary carries cancelled into "cancelled": True, "id": request_id.
        "cancelled": True, "id": request_id,
    # What: apply the grouped expression portion of the enclosing predicate; why: this clause remains in conflicting_request_canary\'s enclosing expression so its grouping and evaluation order stay intact.
    }:
        # What: raise RuntimeError for the caller; why:  conflicting_request_canary stops this rejected path before it can mutate state, dispatch work, or report success.
        raise RuntimeError("active conflicting stream cancellation was not acknowledged")
    # What: gate on wait and seconds and active finished before timeout error; why: conflicting_request_canary admits timeout error only for this predicate and excludes the opposite state.
    if not active_finished.wait(seconds):
        # What: raise TimeoutError for the caller; why:  conflicting_request_canary stops this rejected path before it can mutate state, dispatch work, or report success.
        raise TimeoutError("active conflicting stream did not close")
    # What: call waiting_worker.join with seconds; why: conflicting_request_canary invokes waiting_worker.join while performing if waiting worker is alive or waiting errors or len; the call advances that operation through its result or side effect.
    waiting_worker.join(seconds)
    # What: gate on waiting errors and is alive and waiting worker and len and waiting result before runtime error; why: conflicting_request_canary admits runtime error only for this predicate and excludes the opposite state.
    if waiting_worker.is_alive() or waiting_errors or len(waiting_result) != 1:
        # What: propagate raise RuntimeError waiting model did not complete after active stream cancellation as a qualification failure; why: callers must not continue after this violated precondition or observed result.
        raise RuntimeError("waiting model did not complete after active-stream cancellation")
    # What: compute waiting raw and waiting row from waiting result and 0; why: return bytes active raw waiting raw restored raw later reads waiting raw and waiting row, so conflicting_request_canary must retain the computed value under that name.
    waiting_raw, waiting_row = waiting_result[0]
    # What: compute and after waiting from request json and base and router and status; why: value restored request json base router status later reads and after waiting, so conflicting_request_canary must retain the computed value under that name.
    _, after_waiting = request_json(base + "/router/status")
    # What: gate on waiting model and get and prior activations and waiting row and after waiting before runtime error; why: conflicting_request_canary admits runtime error only for this predicate and excludes the opposite state.
    if (
        # What: call waiting_row.get with passed; why: conflicting_request_canary invokes waiting_row.get while performing or after waiting get active profile waiting model; the call advances that operation through its result or side effect.
        waiting_row.get("passed") is not True
        # What: call after_waiting.get with active profile; why: conflicting_request_canary invokes after_waiting.get while performing or after waiting get active requests; the call advances that operation through its result or side effect.
        or after_waiting.get("activeProfile") != waiting_model
        # What: call after_waiting.get with active requests; why: conflicting_request_canary invokes after_waiting.get while performing or after waiting get activations prior activations; the call advances that operation through its result or side effect.
        or after_waiting.get("activeRequests") != 0
        # What: call after_waiting.get with activations; why: conflicting_request_canary consumes the after_waiting.get return value while evaluating or after_waiting.get("activations") != prior_activations + 1.
        or after_waiting.get("activations") != prior_activations + 1
    # What: complete the enclosing predicate with if waiting row get passed is not true or after waiting get active profile; why: conflicting_request_canary groups the supplied clauses as one enclosing predicate expression before its value is consumed.
    ):
        # What: raise RuntimeError for the caller; why:  conflicting_request_canary stops this rejected path before it can mutate state, dispatch work, or report success.
        raise RuntimeError("waiting model did not receive exactly one post-drain activation")
    # What: compute restored raw and restored row from canary and base and active model and false; why: return bytes active raw waiting raw restored raw later reads restored raw and restored row, so conflicting_request_canary must retain the computed value under that name.
    restored_raw, restored_row = canary(base, active_model, direct=False)
    # What: compute and restored from request json and base and router and status; why: the enclosing return or state update later reads and restored, so conflicting_request_canary must retain the computed value under that name.
    _, restored = request_json(base + "/router/status")
    # What: gate on get and prior activations and restored row and restored before runtime error; why: conflicting_request_canary admits runtime error only for this predicate and excludes the opposite state.
    if restored_row.get("passed") is not True or restored.get("activations") != prior_activations + 2:
        # What: raise RuntimeError for the caller; why:  conflicting_request_canary stops this rejected path before it can mutate state, dispatch work, or report success.
        raise RuntimeError("conflicting-request qualification did not restore model A")
    # What: gate on active raw before runtime error; why: conflicting_request_canary admits runtime error only for this predicate and excludes the opposite state.
    if b"data: [DONE]" in active_raw:
        # What: raise RuntimeError for the caller; why:  conflicting_request_canary stops this rejected path before it can mutate state, dispatch work, or report success.
        raise RuntimeError("active conflicting stream completed normally instead of being cancelled")
    # What: return waiting raw and restored raw and bytes and active raw from conflicting_request_canary; why: conflicting_request_canary exposes waiting raw and restored raw and bytes and active raw so its caller can continue with the function\'s computed outcome.
    return bytes(active_raw), waiting_raw, restored_raw, {
        # What: map the active profile field as active model; why: conflicting_request_canary carries active profile into "activeProfile": active_model, "waitingProfile": waiting_model.
        "activeProfile": active_model, "waitingProfile": waiting_model,
        # What: map the queued behind active field as true; why: conflicting_request_canary carries queued behind active into "queuedBehindActive": True, "activeIdentityPreservedWhileQueued": True.
        "queuedBehindActive": True, "activeIdentityPreservedWhileQueued": True,
        # What: map the activation delta field as 2; why: conflicting_request_canary carries activation delta into "activationDelta": 2, "restoredProfile": active_model, "passed": True.
        "activationDelta": 2, "restoredProfile": active_model, "passed": True,
    # What: execute the grouped source fragment; why:  the enclosing symbol requires this operation for its concrete qualification or routing path.
    }


# What: define stop_process_group around proc; why: its direct callers call stop_process_group for stop process group and rely on this exact input and result contract.
def stop_process_group(proc: subprocess.Popen[bytes]) -> None:
    # What: gate on poll and proc before the computed value; why: stop_process_group admits the computed value only for this predicate and excludes the opposite state.
    if proc.poll() is not None:
        # What: return no value from stop_process_group; why: stop_process_group returns no value to callers that depend on its completed result.
        return
    # What: call os.killpg with pid and proc and sigterm and signal; why: stop_process_group invokes os.killpg while performing try; the call advances that operation through its result or side effect.
    os.killpg(proc.pid, signal.SIGTERM)
    # What: establish the handler boundary for the protected operation; why: stop_process_group routes failures to timeout expired and subprocess while preserving cleanup and success flow.
    try:
        # What: supply timeout to proc.wait; why: stop_process_group binds this 45 value to proc.wait's timeout input.
        proc.wait(timeout=45)
    # What: handle timeout expired and subprocess by os killpg proc pid signal sigkill; why: stop_process_group converts that failure into this concrete recovery, response, or cleanup behavior.
    except subprocess.TimeoutExpired:
        # What: call os.killpg with pid and proc and sigkill and signal; why: stop_process_group invokes os.killpg while performing proc wait timeout; the call advances that operation through its result or side effect.
        os.killpg(proc.pid, signal.SIGKILL)
        # What: supply timeout to proc.wait; why: stop_process_group binds this 10 value to proc.wait's timeout input.
        proc.wait(timeout=10)


# What: define validate_routed_trial around router and alias and prior activations and expected delta; why: its direct callers call validate_routed_trial for validate routed trial and rely on this exact input and result contract.
def validate_routed_trial(router: dict, *, alias: str, prior_activations: int, expected_delta: int) -> int:
    """Prove that a labeled routed benchmark actually used its intended state.

    Timings alone cannot distinguish a warm request from an accidental reload.
    The bounded router state makes each performance label auditable without
    retaining a prompt or model path in the public summary.
    """
    # What: document prove that a labeled routed benchmark in the validate_routed_trial docstring; why: introspection and maintainers read this exact docstring fragment to understand validate routed trial behavior without executing it.
    # What: document timings alone cannot distinguish a warm in the validate_routed_trial docstring; why: introspection and maintainers read this exact docstring fragment to understand validate routed trial behavior without executing it.
    # What: document the bounded router state makes each in the validate_routed_trial docstring; why: introspection and maintainers read this exact docstring fragment to understand validate routed trial behavior without executing it.
    # What: document retaining a prompt or model path in the validate_routed_trial docstring; why: introspection and maintainers read this exact docstring fragment to understand validate routed trial behavior without executing it.
    # What: preserve the paragraph boundary in the the validate_routed_trial docstring; why: introspection and maintainers read this paragraph break to understand validate routed trial behavior without executing it.
    # What: compute activations from get and router and activations; why: if not isinstance activations int or later reads activations, so validate_routed_trial must retain the computed value under that name.
    activations = router.get("activations")
    # What: gate on alias and get and router before runtime error; why: validate_routed_trial admits runtime error only for this predicate and excludes the opposite state.
    if router.get("activeProfile") != alias or router.get("activeRequests") != 0:
        # What: raise RuntimeError for the caller; why:  validate_routed_trial stops this rejected path before it can mutate state, dispatch work, or report success.
        raise RuntimeError("routed trial did not settle on the expected idle profile")
    # What: gate on activations and isinstance and int and prior activations and expected delta before runtime error; why: validate_routed_trial admits runtime error only for this predicate and excludes the opposite state.
    if not isinstance(activations, int) or activations != prior_activations + expected_delta:
        # What: raise RuntimeError for the caller; why:  validate_routed_trial stops this rejected path before it can mutate state, dispatch work, or report success.
        raise RuntimeError("routed trial activation count did not match its scenario")
    # What: return activations from validate_routed_trial; why: validate_routed_trial exposes activations so its caller can continue with the function\'s computed outcome.
    return activations


# What: define valid_periodic_performance around performance; why: its direct callers call valid_periodic_performance for valid periodic performance and rely on this exact input and result contract.
def valid_periodic_performance(performance: dict) -> bool:
    # What: compute rows from get and performance and sys stats; why: or not isinstance rows list later reads rows, so valid_periodic_performance must retain the computed value under that name.
    rows = performance.get("sys_stats")
    # What: gate on get and isinstance and rows and list and all before the computed value; why: valid_periodic_performance admits the computed value only for this predicate and excludes the opposite state.
    if (
        # What: call performance.get with enabled; why: valid_periodic_performance invokes performance.get while performing or performance get gpu stats; the call advances that operation through its result or side effect.
        performance.get("enabled") is not True
        # What: call performance.get with gpu stats; why: valid_periodic_performance invokes performance.get while performing or not isinstance rows list; the call advances that operation through its result or side effect.
        or performance.get("gpu_stats") != []
        # What: call isinstance with rows and list; why: valid_periodic_performance invokes isinstance while performing or not len rows; the call advances that operation through its result or side effect.
        or not isinstance(rows, list)
        # What: call len with rows; why: valid_periodic_performance invokes len while performing or not all; the call advances that operation through its result or side effect.
        or not 1 <= len(rows) <= 720
        # What: call all with row and rows and isinstance and dict; why: valid_periodic_performance invokes all while performing isinstance row dict; the call advances that operation through its result or side effect.
        or not all(
            # What: call isinstance with row and dict; why: valid_periodic_performance invokes isinstance while performing and row get scope engine process tree; the call advances that operation through its result or side effect.
            isinstance(row, dict)
            # What: call row.get with scope; why: valid_periodic_performance invokes row.get while performing and not any key in row; the call advances that operation through its result or side effect.
            and row.get("scope") == "engine-process-tree"
            # What: call any with key and row and pids and model and path; why: valid_periodic_performance invokes any while performing for row in rows; the call advances that operation through its result or side effect.
            and not any(key in row for key in ("pids", "model", "path", "command"))
            # What: apply the for row in rows portion of the enclosing predicate; why: this clause remains in valid_periodic_performance\'s enclosing expression so its grouping and evaluation order stay intact.
            for row in rows
        # What: complete the all call with row; why: valid_periodic_performance groups the supplied clauses as one all call before its value is consumed.
        )
    # What: complete the enclosing predicate with if performance get enabled is not true or performance get gpu stats; why: valid_periodic_performance groups the supplied clauses as one enclosing predicate expression before its value is consumed.
    ):
        # What: return false from valid_periodic_performance; why: valid_periodic_performance exposes false so its caller can continue with the function\'s computed outcome.
        return False
    # What: compute latest from rows and 1; why: latest get ram available is later reads latest, so valid_periodic_performance must retain the computed value under that name.
    latest = rows[-1]
    # What: return isinstance and int and all and get from valid_periodic_performance; why: valid_periodic_performance exposes isinstance and int and all and get so its caller can continue with the function\'s computed outcome.
    return (
        # What: call latest.get with ram available; why: valid_periodic_performance invokes latest.get while performing and latest get vram available is; the call advances that operation through its result or side effect.
        latest.get("ram_available") is True
        # What: call latest.get with vram available; why: valid_periodic_performance invokes latest.get while performing and isinstance latest get ram bytes int; the call advances that operation through its result or side effect.
        and latest.get("vram_available") is True
        # What: call isinstance with get and latest and ram bytes and int; why: valid_periodic_performance invokes isinstance while performing and latest ram bytes; the call advances that operation through its result or side effect.
        and isinstance(latest.get("ram_bytes"), int)
        # What: apply the and latest ram bytes portion of the enclosing predicate; why: this clause remains in valid_periodic_performance\'s enclosing expression so its grouping and evaluation order stay intact.
        and latest["ram_bytes"] > 0
        # What: call isinstance with get and latest and vram bytes and int; why: valid_periodic_performance invokes isinstance while performing and latest vram bytes; the call advances that operation through its result or side effect.
        and isinstance(latest.get("vram_bytes"), int)
        # What: apply the and latest vram bytes portion of the enclosing predicate; why: this clause remains in valid_periodic_performance\'s enclosing expression so its grouping and evaluation order stay intact.
        and latest["vram_bytes"] > 0
        # What: call all with key and isinstance and str and latest; why: valid_periodic_performance invokes all while performing isinstance latest get key str and latest; the call advances that operation through its result or side effect.
        and all(
            # What: call isinstance with get and key and latest and str; why: valid_periodic_performance invokes isinstance while performing for key in timestamp ram source vram source; the call advances that operation through its result or side effect.
            isinstance(latest.get(key), str) and latest[key]
            # What: apply the for key in timestamp ram source vram source portion of the enclosing predicate; why: this clause remains in valid_periodic_performance\'s enclosing expression so its grouping and evaluation order stay intact.
            for key in ("timestamp", "ram_source", "vram_source")
        # What: complete the all call with key; why: valid_periodic_performance groups the supplied clauses as one all call before its value is consumed.
        )
    # What: complete the valid_periodic_performance signature with performance; why: valid_periodic_performance groups the supplied clauses as one valid_periodic_performance signature before its value is consumed.
    )


# What: define control_plane_canary around base and artifacts; why: its direct callers call control_plane_canary for control plane canary and rely on this exact input and result contract.
def control_plane_canary(base: str, artifacts: Path) -> dict:
    """Qualify authenticated management, metrics, and bounded router-log access."""
    # What: document qualify authenticated management metrics and bounded in the control_plane_canary docstring; why: introspection and maintainers read this exact docstring fragment to understand control plane canary behavior without executing it.
    # What: initialize unauthorized as an empty runtime accumulator; why: control_plane_canary appends or maps entries into it during unauthorized path exc code before consuming the aggregate.
    unauthorized: dict[str, int] = {}
    # What: compute protected paths from router and status and v1 and models and models; why: for path in protected paths later reads protected paths, so control_plane_canary must retain the computed value under that name.
    protected_paths = ("/router/status", "/v1/models", "/models", "/api/performance")
    # What: iterate across protected paths to perform request and request and base and path and urllib; why: control_plane_canary repeats the body only while or for the loop header admits an iteration.
    for path in protected_paths:
        # What: compute request from request and request and base and path; why: with urllib request urlopen request timeout later reads request, so control_plane_canary must retain the computed value under that name.
        request = urllib.request.Request(base + path)
        # What: establish the handler boundary for the protected operation; why: control_plane_canary routes failures to httperror and error and urllib while preserving cleanup and success flow.
        try:
            # What: enter the urllib.request.urlopen managed context before pass; why: control_plane_canary releases this resource or lock after pass on both success and failure paths.
            with urllib.request.urlopen(request, timeout=10):
                # What: ignore the anticipated exception handled by this branch; why: control_plane_canary continues its retry or cleanup path instead of re-raising that transient failure.
                pass
        # What: handle httperror and error and urllib by unauthorized path exc code; why: control_plane_canary converts that failure into this concrete recovery, response, or cleanup behavior.
        except urllib.error.HTTPError as exc:
            # What: compute unauthorized entry from code and exc; why: if unauthorized path for path in later reads unauthorized entry, so control_plane_canary must retain the computed value under that name.
            unauthorized[path] = exc.code
            # What: call exc.close with the declared inputs; why: control_plane_canary invokes exc.close while performing else; the call advances that operation through its result or side effect.
            exc.close()
        # What: select the remaining branch that performs raise runtime error f unauthenticated request unexpectedly; why: control_plane_canary covers the state excluded by the preceding predicate without conflating the two outcomes.
        else:
            # What: raise RuntimeError for the caller; why:  control_plane_canary stops this rejected path before it can mutate state, dispatch work, or report success.
            raise RuntimeError(f"unauthenticated request unexpectedly succeeded: {path}")
    # What: gate on unauthorized and path and protected paths before runtime error; why: control_plane_canary admits runtime error only for this predicate and excludes the opposite state.
    if unauthorized != {path: 401 for path in protected_paths}:
        # What: raise RuntimeError for the caller; why:  control_plane_canary stops this rejected path before it can mutate state, dispatch work, or report success.
        raise RuntimeError("native router did not reject unauthenticated control and inference")

    # What: gate on native auth base and native api key and rstrip and base before runtime error; why: control_plane_canary admits runtime error only for this predicate and excludes the opposite state.
    if _NATIVE_AUTH_BASE != base.rstrip("/") or _NATIVE_API_KEY is None:
        # What: raise RuntimeError for the caller; why:  control_plane_canary stops this rejected path before it can mutate state, dispatch work, or report success.
        raise RuntimeError("native router credentials are not scoped to the qualification origin")
    # What: compute basic from decode and b64encode and base64 and encode; why: basic authorization f basic basic later reads basic, so control_plane_canary must retain the computed value under that name.
    basic = base64.b64encode(f"operator:{_NATIVE_API_KEY}".encode()).decode()
    # What: initialize alternate auth raw as an empty runtime accumulator; why: control_plane_canary appends or maps entries into it during alternate auth raw name raw before consuming the aggregate.
    alternate_auth_raw: dict[str, bytes] = {}
    # What: iterate across native api key and basic to perform request and request and base and headers and urllib; why: control_plane_canary repeats the body only while or for the loop header admits an iteration.
    for name, headers in (
        # What: map the authorization field as basic and basic; why: control_plane_canary carries authorization through ("basic", {"Authorization": f"Basic {basic}"}) into raise runtime error models is not equivalent to.
        ("basic", {"Authorization": f"Basic {basic}"}),
        # What: map the x api key field as native api key; why: control_plane_canary carries x api key through ("x-api-key", {"X-Api-Key": _NATIVE_API_KEY}) into raise runtime error models is not equivalent to.
        ("x-api-key", {"X-Api-Key": _NATIVE_API_KEY}),
    # What: complete the enclosing predicate collection with basic and basic and authorization and basic and native api key and x api key and x api key; why: control_plane_canary groups the supplied clauses as one enclosing predicate collection collection before its value is consumed.
    ):
        # What: compute request from request and request and base and headers; why: with urllib request urlopen request timeout as response later reads request, so control_plane_canary must retain the computed value under that name.
        request = urllib.request.Request(base + "/router/status", headers=headers)
        # What: enter the urllib.request.urlopen managed context before raw response read; why: control_plane_canary releases this resource or lock after raw response read on both success and failure paths.
        with urllib.request.urlopen(request, timeout=10) as response:
            # What: compute raw from read and response; why: status json loads raw later reads raw, so control_plane_canary must retain the computed value under that name.
            raw = response.read()
        # What: compute status from loads and raw and json; why: if status get active profile model a later reads status, so control_plane_canary must retain the computed value under that name.
        status = json.loads(raw)
        # What: gate on get and status before runtime error and name; why: control_plane_canary admits runtime error and name only for this predicate and excludes the opposite state.
        if status.get("activeProfile") != "model-a":
            # What: raise RuntimeError for the caller; why:  control_plane_canary stops this rejected path before it can mutate state, dispatch work, or report success.
            raise RuntimeError(f"{name} authentication did not expose exact model-a residency")
        # What: compute alternate auth raw entry from raw; why: for name raw in alternate auth raw items later reads alternate auth raw entry, so control_plane_canary must retain the computed value under that name.
        alternate_auth_raw[name] = raw

    # What: compute models raw and models from request json and base and v1 and models and 10; why: artifacts control v1 models json write bytes models raw later reads models raw and models, so control_plane_canary must retain the computed value under that name.
    models_raw, models = request_json(base + "/v1/models", timeout=10)
    # What: compute and models alias from request json and base and models and 10; why: value namespaced stats request json later reads and models alias, so control_plane_canary must retain the computed value under that name.
    _, models_alias = request_json(base + "/models", timeout=10)
    # What: establish a diagnostic boundary around namespaced upstream stats; why: a live proxy rejection must retain its private response body instead of collapsing to an opaque HTTP status.
    try:
        # What: request stats through the slash-namespaced alias; why: the control plane must prove longest-prefix alias resolution against the resident engine.
        _, namespaced_stats = request_json(
            # What: supply the bounded timeout to the stats request; why: qualification must not wait indefinitely on a broken upstream proxy.
            base + "/upstream/compat/model-a/v1/stats", timeout=10
        # What: complete the namespaced stats request; why: the returned mapping is validated with the remaining authenticated control-plane evidence.
        )
    # What: catch an HTTP rejection from the live proxy; why: the exact private error payload is required to distinguish path parsing, residency, and upstream failures.
    except urllib.error.HTTPError as exc:
        # What: read and decode the bounded rejection body; why: diagnostics must remain useful without allowing an unbounded error response into artifacts.
        error_body = exc.read(64 * 1024).decode("utf-8", errors="replace")
        # What: raise a contextual qualification error chained to the protocol failure; why: the harness must fail closed while preserving the actionable reason.
        raise RuntimeError(f"namespaced stats HTTP {exc.code}: {error_body}") from exc
    # What: compute routed raw and routed from request json and base and router and models and 10; why: artifacts control router models json write bytes routed raw later reads routed raw and routed, so control_plane_canary must retain the computed value under that name.
    routed_raw, routed = request_json(base + "/router/models", timeout=10)
    # What: compute profiles raw and profiles from request json and base and router and profiles and 10; why: artifacts control router profiles json write bytes profiles raw later reads profiles raw and profiles, so control_plane_canary must retain the computed value under that name.
    profiles_raw, profiles = request_json(base + "/router/profiles", timeout=10)
    # What: compute performance raw from the named fixture input; why: performance raw performance request json base api performance later reads performance raw, so control_plane_canary must retain the computed value under that name.
    performance_raw = b""
    # What: initialize performance as an empty runtime accumulator; why: control_plane_canary appends or maps entries into it during performance raw performance request json base api performance timeout before consuming the aggregate.
    performance: dict = {}
    # What: compute performance deadline from monotonic and time and 15; why: if time monotonic performance deadline later reads performance deadline, so control_plane_canary must retain the computed value under that name.
    performance_deadline = time.monotonic() + 15
    # What: iterate across the computed value to perform performance raw and performance and request json and base; why: control_plane_canary repeats the body only while or for the loop header admits an iteration.
    while True:
        # What: compute performance raw and performance from request json and base and api and performance and 10; why: control_plane_canary consumes performance raw and performance during artifacts control performance json write bytes performance raw, so performance raw and performance value receives the computed val.
        performance_raw, performance = request_json(base + "/api/performance", timeout=10)
        # What: gate on valid periodic performance and performance before the computed value; why: control_plane_canary admits the computed value only for this predicate and excludes the opposite state.
        if valid_periodic_performance(performance):
            # What: apply the break portion of the enclosing predicate; why: this clause remains in control_plane_canary\'s enclosing expression so its grouping and evaluation order stay intact.
            break
        # What: gate on performance deadline and monotonic and time before runtime error; why: control_plane_canary admits runtime error only for this predicate and excludes the opposite state.
        if time.monotonic() >= performance_deadline:
            # What: raise RuntimeError for the caller; why:  control_plane_canary stops this rejected path before it can mutate state, dispatch work, or report success.
            raise RuntimeError("periodic performance lacked a positive owned-process sample")
        # What: call time.sleep with 0 25; why: control_plane_canary invokes time.sleep while performing metrics raw request bytes base metrics timeout; the call advances that operation through its result or side effect.
        time.sleep(0.25)
    # What: compute metrics raw from request bytes and base and metrics and 10; why: or b freetoken swap admissions total not in metrics raw later reads metrics raw, so control_plane_canary must retain the computed value under that name.
    metrics_raw = request_bytes(base + "/metrics", timeout=10)
    # What: compute model rows from get and models and data; why: for rows in model rows alias rows routed rows later reads model rows, so control_plane_canary must retain the computed value under that name.
    model_rows = models.get("data")
    # What: compute alias rows from get and models alias and data; why: for rows in model rows alias rows routed rows later reads alias rows, so control_plane_canary must retain the computed value under that name.
    alias_rows = models_alias.get("data")
    # What: compute routed rows from get and routed and data; why: for rows in model rows alias rows routed rows later reads routed rows, so control_plane_canary must retain the computed value under that name.
    routed_rows = routed.get("data")
    # What: compute profile rows from get and profiles and data; why: for rows in model rows alias rows routed rows later reads profile rows, so control_plane_canary must retain the computed value under that name.
    profile_rows = profiles.get("data")
    # What: compute routing profiles from get and profiles and routing profiles; why: item for item in routing profiles later reads routing profiles, so control_plane_canary must retain the computed value under that name.
    routing_profiles = profiles.get("routingProfiles")
    # What: gate on all and rows and isinstance and list and model rows before runtime error; why: control_plane_canary admits runtime error only for this predicate and excludes the opposite state.
    if not all(
        # What: call isinstance with rows and list; why: control_plane_canary invokes isinstance while performing for rows in model rows alias rows routed rows; the call advances that operation through its result or side effect.
        isinstance(rows, list) and all(isinstance(item, dict) for item in rows)
        # What: apply the for rows in model rows alias rows routed rows portion of the enclosing predicate; why: this clause remains in control_plane_canary\'s enclosing expression so its grouping and evaluation order stay intact.
        for rows in (model_rows, alias_rows, routed_rows, profile_rows)
    # What: complete the all call with rows; why: control_plane_canary groups the supplied clauses as one all call before its value is consumed.
    ):
        # What: raise RuntimeError for the caller; why:  control_plane_canary stops this rejected path before it can mutate state, dispatch work, or report success.
        raise RuntimeError("authenticated native control-plane responses have invalid shapes")
    # The pinned alias invokes the same handler independently, so request-time
    # `created` values may differ by one second. Everything else must match.
    # What: compute normalized models from k and v and item and model rows; why: if model envelope alias envelope or normalized models normalized alias later reads normalized models, so control_plane_canary must retain the computed value under that name.
    normalized_models = [{k: v for k, v in item.items() if k != "created"} for item in model_rows]
    # What: compute normalized alias from k and v and item and alias rows; why: if model envelope alias envelope or normalized models normalized alias later reads normalized alias, so control_plane_canary must retain the computed value under that name.
    normalized_alias = [{k: v for k, v in item.items() if k != "created"} for item in alias_rows]
    # What: compute model envelope from k and v and items and models and data; why: if model envelope alias envelope or normalized models normalized alias later reads model envelope, so control_plane_canary must retain the computed value under that name.
    model_envelope = {k: v for k, v in models.items() if k != "data"}
    # What: compute alias envelope from k and v and items and models alias and data; why: if model envelope alias envelope or normalized models normalized alias later reads alias envelope, so control_plane_canary must retain the computed value under that name.
    alias_envelope = {k: v for k, v in models_alias.items() if k != "data"}
    # What: gate on model envelope and alias envelope and normalized models and normalized alias before runtime error; why: control_plane_canary admits runtime error only for this predicate and excludes the opposite state.
    if model_envelope != alias_envelope or normalized_models != normalized_alias:
        # What: raise RuntimeError for the caller; why:  control_plane_canary stops this rejected path before it can mutate state, dispatch work, or report success.
        raise RuntimeError("/models is not equivalent to the /v1/models compatibility listing")
    # What: compute aliases from sorted and item and model rows and isinstance; why: not model a model b compat model a preferred model later reads aliases, so control_plane_canary must retain the computed value under that name.
    aliases = sorted(item["id"] for item in model_rows if isinstance(item.get("id"), str))
    # What: compute routed names from sorted and item and routed rows and isinstance; why: or routed names profile names later reads routed names, so control_plane_canary must retain the computed value under that name.
    routed_names = sorted(
        # What: call isinstance with get and item and name and str; why: control_plane_canary consumes the isinstance return value while evaluating item["name"] for item in routed_rows if isinstance(item.get("name"), str.
        item["name"] for item in routed_rows if isinstance(item.get("name"), str)
    # What: complete the sorted call with item; why: control_plane_canary groups the supplied clauses as one sorted call before its value is consumed.
    )
    # What: compute profile names from sorted and item and profile rows and isinstance; why: or routed names profile names later reads profile names, so control_plane_canary must retain the computed value under that name.
    profile_names = sorted(
        # What: call isinstance with get and item and name and str; why: control_plane_canary consumes the isinstance return value while evaluating item["name"] for item in profile_rows if isinstance(item.get("name"), st.
        item["name"] for item in profile_rows if isinstance(item.get("name"), str)
    # What: complete the sorted call with item; why: control_plane_canary groups the supplied clauses as one sorted call before its value is consumed.
    )
    # What: compute coding profile from isinstance and routing profiles and list and next; why: or not isinstance coding profile dict later reads coding profile, so control_plane_canary must retain the computed value under that name.
    coding_profile = next(
        # What: complete the next call with item; why:  control_plane_canary groups the supplied clauses as one next call before its value is consumed.
        (
            # What: apply the item for item in routing profiles portion of coding profile; why: control_plane_canary uses this clause to evaluate coding profile as one grouped value.
            item for item in routing_profiles
            # What: call isinstance with item and dict; why: control_plane_canary consumes the isinstance return value while evaluating if isinstance(item, dict) and item.get("name") == "coding".
            if isinstance(item, dict) and item.get("name") == "coding"
        # What: complete the next call with item; why:  control_plane_canary groups the supplied clauses as one next call before its value is consumed.
        ),
        # What: apply the grouped expression portion of coding profile; why: control_plane_canary uses this clause to evaluate coding profile as one grouped value.
        None,
    # What: call isinstance with routing profiles and list; why: control_plane_canary invokes isinstance while performing resident item get name for item in; the call advances that operation through its result or side effect.
    ) if isinstance(routing_profiles, list) else None
    # What: compute resident from get and item and routed rows and name and resident; why: or resident model a later reads resident, so control_plane_canary must retain the computed value under that name.
    resident = [item.get("name") for item in routed_rows if item.get("resident")]
    # What: compute routed a from next and item and routed rows and get and model a; why: or not isinstance routed a dict later reads routed a, so control_plane_canary must retain the computed value under that name.
    routed_a = next((item for item in routed_rows if item.get("name") == "model-a"), None)
    # What: compute listed a from next and item and model rows and get and model a; why: or not isinstance listed a dict later reads listed a, so control_plane_canary must retain the computed value under that name.
    listed_a = next((item for item in model_rows if item.get("id") == "model-a"), None)
    # What: compute listed alias a from next and item and model rows and get and compat; why: or not isinstance listed alias a dict later reads listed alias a, so control_plane_canary must retain the computed value under that name.
    listed_alias_a = next(
        # What: call item.get with id; why: control_plane_canary consumes the item.get return value while evaluating (item for item in model_rows if item.get("id") == "compat/model-a"), Non.
        (item for item in model_rows if item.get("id") == "compat/model-a"), None
    # What: complete the next call with item; why:  control_plane_canary groups the supplied clauses as one next call before its value is consumed.
    )
    # What: gate on routed names and profile names and resident and metrics raw and issubset before runtime error; why: control_plane_canary admits runtime error only for this predicate and excludes the opposite state.
    if (
        # What: call operation.issubset with aliases; why: control_plane_canary invokes operation.issubset while performing or routed names profile names; the call advances that operation through its result or side effect.
        not {"model-a", "model-b", "compat/model-a", "preferred-model"}.issubset(aliases)
        # What: apply the or routed names profile names portion of the enclosing predicate; why: this clause remains in control_plane_canary\'s enclosing expression so its grouping and evaluation order stay intact.
        or routed_names != profile_names
        # What: call operation.issubset with routed names; why: control_plane_canary invokes operation.issubset while performing or resident model a; the call advances that operation through its result or side effect.
        or not {"model-a", "model-b"}.issubset(routed_names)
        # What: apply the or resident model a portion of the enclosing predicate; why: this clause remains in control_plane_canary\'s enclosing expression so its grouping and evaluation order stay intact.
        or resident != ["model-a"]
        # What: call profiles.get with active profile; why: control_plane_canary invokes profiles.get while performing or profiles get active routing profile is not; the call advances that operation through its result or side effect.
        or profiles.get("activeProfile") != "model-a"
        # What: call profiles.get with active routing profile; why: control_plane_canary invokes profiles.get while performing or not isinstance routing profiles list; the call advances that operation through its result or side effect.
        or profiles.get("activeRoutingProfile") is not None
        # What: call isinstance with routing profiles and list; why: control_plane_canary invokes isinstance while performing or not isinstance coding profile dict; the call advances that operation through its result or side effect.
        or not isinstance(routing_profiles, list)
        # What: call isinstance with coding profile and dict; why: control_plane_canary invokes isinstance while performing or coding profile get pins; the call advances that operation through its result or side effect.
        or not isinstance(coding_profile, dict)
        # What: call coding_profile.get with pins; why: control_plane_canary invokes coding_profile.get while performing disabled model profile model preferred model; the call advances that operation through its result or side effect.
        or coding_profile.get("pins") != {
            # What: map the disabled model field as the fixture input; why: control_plane_canary carries disabled model through "disabled-model": None, "profile-model": "preferred-model" into raise runtime error router log stream lacked the.
            "disabled-model": None, "profile-model": "preferred-model",
        # What: complete the enclosing predicate mapping with disabled model and profile model; why: control_plane_canary groups the supplied clauses as one enclosing predicate mapping mapping before its value is consumed.
        }
        # What: call isinstance with routed a and dict; why: control_plane_canary invokes isinstance while performing or routed a get check endpoint ready; the call advances that operation through its result or side effect.
        or not isinstance(routed_a, dict)
        # What: call routed_a.get with check endpoint; why: control_plane_canary invokes routed_a.get while performing or routed a get use model name model a; the call advances that operation through its result or side effect.
        or routed_a.get("checkEndpoint") != "/ready"
        # What: call routed_a.get with use model name; why: control_plane_canary invokes routed_a.get while performing or routed a get upstream timeout s; the call advances that operation through its result or side effect.
        or routed_a.get("useModelName") != "model-a"
        # What: call routed_a.get with upstream timeout s; why: control_plane_canary invokes routed_a.get while performing or routed a get display name qualification model a; the call advances that operation through its result or side effect.
        or routed_a.get("upstreamTimeoutS") != 659
        # What: call routed_a.get with display name; why: control_plane_canary invokes routed_a.get while performing or routed a get metadata tier qualification type; the call advances that operation through its result or side effect.
        or routed_a.get("displayName") != "Qualification model A"
        # What: map the tier field as qualification; why: control_plane_canary carries tier through or routed_a.get("metadata") != {"tier": "qualification", "type": "operat into raise runtime error router log stream lacked the.
        or routed_a.get("metadata") != {"tier": "qualification", "type": "operator"}
        # What: call isinstance with listed a and dict; why: control_plane_canary invokes isinstance while performing or listed a get name qualification model a; the call advances that operation through its result or side effect.
        or not isinstance(listed_a, dict)
        # What: call listed_a.get with name; why: control_plane_canary invokes listed_a.get while performing or listed a get meta get freetoken; the call advances that operation through its result or side effect.
        or listed_a.get("name") != "Qualification model A"
        # What: call operation.get with freetoken; why: control_plane_canary invokes operation.get while performing aliases compat model a tier qualification type; the call advances that operation through its result or side effect.
        or listed_a.get("meta", {}).get("freetoken") != {
            # What: map the aliases field as compat and model a; why: control_plane_canary carries aliases through "aliases": ["compat/model-a"], "tier": "qualification", "type": "model" into raise runtime error router log stream lacked the.
            "aliases": ["compat/model-a"], "tier": "qualification", "type": "model",
        # What: complete the enclosing predicate mapping with aliases and tier and type; why: control_plane_canary groups the supplied clauses as one enclosing predicate mapping mapping before its value is consumed.
        }
        # What: call isinstance with listed alias a and dict; why: control_plane_canary invokes isinstance while performing or listed alias a get name qualification model a; the call advances that operation through its result or side effect.
        or not isinstance(listed_alias_a, dict)
        # What: call listed_alias_a.get with name; why: control_plane_canary invokes listed_alias_a.get while performing or listed alias a get meta get freetoken; the call advances that operation through its result or side effect.
        or listed_alias_a.get("name") != "Qualification model A"
        # What: call operation.get with freetoken; why: control_plane_canary invokes operation.get while performing model id model a tier qualification type alias; the call advances that operation through its result or side effect.
        or listed_alias_a.get("meta", {}).get("freetoken") != {
            # What: map the model id field as model a; why: control_plane_canary carries model id through "modelID": "model-a", "tier": "qualification", "type": "alias" into raise runtime error router log stream lacked the.
            "modelID": "model-a", "tier": "qualification", "type": "alias",
        # What: complete the enclosing predicate mapping with model id and tier and type; why: control_plane_canary groups the supplied clauses as one enclosing predicate mapping mapping before its value is consumed.
        }
        # What: call isinstance with namespaced stats and dict; why: control_plane_canary invokes isinstance while performing or b freetoken swap admissions total not in metrics raw; the call advances that operation through its result or side effect.
        or not isinstance(namespaced_stats, dict)
        # What: apply the or b freetoken swap admissions total not in metrics raw portion of the enclosing predicate; why: this clause remains in control_plane_canary\'s enclosing expression so its grouping and evaluation order stay intact.
        or b"freetoken_swap_admissions_total" not in metrics_raw
    # What: complete the enclosing predicate with if not model a model b compat model a preferred model issubset aliases; why: control_plane_canary groups the supplied clauses as one enclosing predicate expression before its value is consumed.
    ):
        # What: raise RuntimeError for the caller; why:  control_plane_canary stops this rejected path before it can mutate state, dispatch work, or report success.
        raise RuntimeError("authenticated native control-plane responses are inconsistent")

    # What: compute log request from request and request and base and urllib; why: with urllib request urlopen log request timeout as response later reads log request, so control_plane_canary must retain the computed value under that name.
    log_request = urllib.request.Request(
        # What: supply headers to _native_headers; why: control_plane_canary binds this native headers and base value to _native_headers's headers input.
        base + "/router/logs?since=0", headers=_native_headers(base)
    # What: complete the urllib.request.Request call with headers; why: control_plane_canary groups the supplied clauses as one urllib.request.Request call before its value is consumed.
    )
    # What: compute log frame from bytearray; why: while len log frame later reads log frame, so control_plane_canary must retain the computed value under that name.
    log_frame = bytearray()
    # What: enter the urllib.request.urlopen managed context before if response headers get content type text event stream; why: control_plane_canary releases this resource or lock after if response headers get content type text event stream on both success and failure paths.
    with urllib.request.urlopen(log_request, timeout=10) as response:
        # What: gate on get content type and headers and response before runtime error; why: control_plane_canary admits runtime error only for this predicate and excludes the opposite state.
        if response.headers.get_content_type() != "text/event-stream":
            # What: raise RuntimeError for the caller; why:  control_plane_canary stops this rejected path before it can mutate state, dispatch work, or report success.
            raise RuntimeError("router log endpoint did not return SSE")
        # What: iterate across len and log frame to perform line and readline and response; why: control_plane_canary repeats the body only while or for the loop header admits an iteration.
        while len(log_frame) <= 64 * 1024:
            # What: compute line from readline and response; why: if not line later reads line, so control_plane_canary must retain the computed value under that name.
            line = response.readline()
            # What: gate on line before the computed value; why: control_plane_canary admits the computed value only for this predicate and excludes the opposite state.
            if not line:
                # What: apply the break portion of the enclosing predicate; why: this clause remains in control_plane_canary\'s enclosing expression so its grouping and evaluation order stay intact.
                break
            # What: call log_frame.extend with line; why: control_plane_canary invokes log_frame.extend while performing if b management loaded in log frame; the call advances that operation through its result or side effect.
            log_frame.extend(line)
            # What: gate on log frame before the computed value; why: control_plane_canary admits the computed value only for this predicate and excludes the opposite state.
            if b"management_loaded" in log_frame:
                # What: apply the break portion of the enclosing predicate; why: this clause remains in control_plane_canary\'s enclosing expression so its grouping and evaluation order stay intact.
                break
    # What: gate on log frame and len before runtime error; why: control_plane_canary admits runtime error only for this predicate and excludes the opposite state.
    if len(log_frame) > 64 * 1024 or b"management_loaded" not in log_frame:
        # What: raise RuntimeError for the caller; why:  control_plane_canary stops this rejected path before it can mutate state, dispatch work, or report success.
        raise RuntimeError("router log stream lacked the bounded management event")

    # What: preserve the exact artifacts control v1 models json write bytes models raw literal fragment; why: control_plane_canary passes this fragment verbatim through (artifacts / "control-v1-models.json").write_bytes(models_raw), because changing it would alter a protocol payload, serialized fixture, or public mess.
    (artifacts / "control-v1-models.json").write_bytes(models_raw)
    # What: preserve the exact artifacts control router models json write bytes routed raw literal fragment; why: control_plane_canary passes this fragment verbatim through (artifacts / "control-router-models.json").write_bytes(routed_raw), because changing it would alter a protocol payload, serialized fixture, or pub.
    (artifacts / "control-router-models.json").write_bytes(routed_raw)
    # What: preserve the exact artifacts control router profiles json write bytes profiles raw literal fragment; why: control_plane_canary passes this fragment verbatim through (artifacts / "control-router-profiles.json").write_bytes(profiles_raw), because changing it would alter a protocol payload, serialized fixture.
    (artifacts / "control-router-profiles.json").write_bytes(profiles_raw)
    # What: preserve the exact artifacts control performance json write bytes performance raw literal fragment; why: control_plane_canary passes this fragment verbatim through (artifacts / "control-performance.json").write_bytes(performance_raw), because changing it would alter a protocol payload, serialized fixture.
    (artifacts / "control-performance.json").write_bytes(performance_raw)
    # What: preserve the exact artifacts control metrics prom write bytes metrics raw literal fragment; why: control_plane_canary passes this fragment verbatim through (artifacts / "control-metrics.prom").write_bytes(metrics_raw), because changing it would alter a protocol payload, serialized fixture, or public messag.
    (artifacts / "control-metrics.prom").write_bytes(metrics_raw)
    # What: preserve the exact artifacts control router log sse write bytes log frame literal fragment; why: control_plane_canary passes this fragment verbatim through (artifacts / "control-router-log.sse").write_bytes(log_frame), because changing it would alter a protocol payload, serialized fixture, or public messag.
    (artifacts / "control-router-log.sse").write_bytes(log_frame)
    # What: iterate across items and alternate auth raw to perform write bytes and raw and artifacts and name; why: control_plane_canary repeats the body only while or for the loop header admits an iteration.
    for name, raw in alternate_auth_raw.items():
        # What: preserve the exact artifacts f control auth name json write bytes literal fragment; why: control_plane_canary passes this fragment verbatim through (artifacts / f"control-auth-{name}.json").write_bytes(raw), because changing it would alter a protocol payload, serialized fixture, or public message.
        (artifacts / f"control-auth-{name}.json").write_bytes(raw)
    # What: return; why:  the caller consumes this value as the function’s success-path result.
    return {
        # What: map the unauthenticated control rejected field as true; why: control_plane_canary carries unauthenticated control rejected into "unauthenticatedControlRejected": True.
        "unauthenticatedControlRejected": True,
        # What: map the unauthenticated inference rejected field as true; why: control_plane_canary carries unauthenticated inference rejected into "unauthenticatedInferenceRejected": True.
        "unauthenticatedInferenceRejected": True,
        # What: map the alias count field as len and aliases; why: control_plane_canary carries alias count into "aliasCount": len(aliases).
        "aliasCount": len(aliases),
        # What: map the selector listed field as aliases and preferred model; why: control_plane_canary carries selector listed into "selectorListed": "preferred-model" in aliases.
        "selectorListed": "preferred-model" in aliases,
        # What: map the profile count field as len and profile names; why: control_plane_canary carries profile count into "profileCount": len(profile_names).
        "profileCount": len(profile_names),
        # What: map the routing profile listed field as true; why: control_plane_canary carries routing profile listed into "routingProfileListed": True.
        "routingProfileListed": True,
        # What: map the configured readiness target verified field as true; why: control_plane_canary carries configured readiness target verified into "configuredReadinessTargetVerified": True.
        "configuredReadinessTargetVerified": True,
        # What: map the configured upstream model name verified field as true; why: control_plane_canary carries configured upstream model name verified into "configuredUpstreamModelNameVerified": True.
        "configuredUpstreamModelNameVerified": True,
        # What: map the configured upstream timeout verified field as true; why: control_plane_canary carries configured upstream timeout verified into "configuredUpstreamTimeoutVerified": True.
        "configuredUpstreamTimeoutVerified": True,
        # What: map the configured model metadata verified field as true; why: control_plane_canary carries configured model metadata verified into "configuredModelMetadataVerified": True.
        "configuredModelMetadataVerified": True,
        # What: map the resident profile field as model a; why: control_plane_canary carries resident profile into "residentProfile": "model-a".
        "residentProfile": "model-a",
        # What: map the model list alias verified field as true; why: control_plane_canary carries model list alias verified into "modelListAliasVerified": True.
        "modelListAliasVerified": True,
        # What: map the namespaced upstream verified field as true; why: control_plane_canary carries namespaced upstream verified into "namespacedUpstreamVerified": True.
        "namespacedUpstreamVerified": True,
        # What: map the api key forms verified field as bearer and basic and x api key; why: control_plane_canary carries api key forms verified into "apiKeyFormsVerified": ["bearer", "basic", "x-api-key"].
        "apiKeyFormsVerified": ["bearer", "basic", "x-api-key"],
        # What: map the metrics available field as true; why: control_plane_canary carries metrics available into "metricsAvailable": True.
        "metricsAvailable": True,
        # What: map the periodic performance available field as true; why: control_plane_canary carries periodic performance available into "periodicPerformanceAvailable": True.
        "periodicPerformanceAvailable": True,
        # What: map the router log sse available field as true; why: control_plane_canary carries router log sse available into "routerLogSseAvailable": True.
        "routerLogSseAvailable": True,
        # What: map the passed field as true; why: control_plane_canary carries passed into "passed": True.
        "passed": True,
    # What: execute the grouped source fragment; why:  the enclosing symbol requires this operation for its concrete qualification or routing path.
    }


# What: define selector_canary around base and artifacts; why: its direct callers call selector_canary for selector canary and rely on this exact input and result contract.
def selector_canary(base: str, artifacts: Path) -> dict:
    """Prove a warm virtual ID reuses the resident target without a swap."""
    # What: document prove a warm virtual id reuses in the selector_canary docstring; why: introspection and maintainers read this exact docstring fragment to understand selector canary behavior without executing it.
    # What: compute and before from request json and base and router and status; why: value after request json base router status later reads and before, so selector_canary must retain the computed value under that name.
    _, before = request_json(base + "/router/status")
    # What: compute prior activations from get and before and activations; why: if before get active profile model a or not later reads prior activations, so selector_canary must retain the computed value under that name.
    prior_activations = before.get("activations")
    # What: gate on get and isinstance and prior activations and int and before before runtime error; why: selector_canary admits runtime error only for this predicate and excludes the opposite state.
    if before.get("activeProfile") != "model-a" or not isinstance(prior_activations, int):
        # What: raise RuntimeError for the caller; why:  selector_canary stops this rejected path before it can mutate state, dispatch work, or report success.
        raise RuntimeError("warm selector canary requires resident model-a")
    # What: compute raw and completion from canary and base and preferred model and false; why: artifacts warm selector sse write bytes raw later reads raw and completion, so selector_canary must retain the computed value under that name.
    raw, completion = canary(base, "preferred-model", direct=False)
    # What: compute and after from request json and base and router and status; why: the enclosing return or state update later reads and after, so selector_canary must retain the computed value under that name.
    _, after = request_json(base + "/router/status")
    # What: gate on prior activations and get and completion and after before runtime error; why: selector_canary admits runtime error only for this predicate and excludes the opposite state.
    if (
        # What: call completion.get with passed; why: selector_canary invokes completion.get while performing or after get active profile model a; the call advances that operation through its result or side effect.
        completion.get("passed") is not True
        # What: call after.get with active profile; why: selector_canary invokes after.get while performing or after get active requests; the call advances that operation through its result or side effect.
        or after.get("activeProfile") != "model-a"
        # What: call after.get with active requests; why: selector_canary invokes after.get while performing or after get activations prior activations; the call advances that operation through its result or side effect.
        or after.get("activeRequests") != 0
        # What: call after.get with activations; why: selector_canary consumes the after.get return value while evaluating or after.get("activations") != prior_activations.
        or after.get("activations") != prior_activations
    # What: complete the enclosing predicate with if completion get passed is not true or after get active profile; why: selector_canary groups the supplied clauses as one enclosing predicate expression before its value is consumed.
    ):
        # What: raise RuntimeError for the caller; why:  selector_canary stops this rejected path before it can mutate state, dispatch work, or report success.
        raise RuntimeError("warm selector did not reuse the resident target")
    # What: preserve the exact artifacts warm selector sse write bytes raw literal fragment; why: selector_canary passes this fragment verbatim through (artifacts / "warm-selector.sse").write_bytes(raw), because changing it would alter a protocol payload, serialized fixture, or public message.
    (artifacts / "warm-selector.sse").write_bytes(raw)
    # What: return strategy and resolved profile and activation delta and passed and warm from selector_canary; why: selector_canary exposes strategy and resolved profile and activation delta and passed and warm so its caller can continue with the function\'s computed outcome.
    return {
        # What: map the strategy field as warm; why: selector_canary carries strategy into "strategy": "warm".
        "strategy": "warm",
        # What: map the resolved profile field as model a; why: selector_canary carries resolved profile into "resolvedProfile": "model-a".
        "resolvedProfile": "model-a",
        # What: map the activation delta field as 0; why: selector_canary carries activation delta into "activationDelta": 0.
        "activationDelta": 0,
        # What: map the passed field as true; why: selector_canary carries passed into "passed": True.
        "passed": True,
    # What: complete the enclosing predicate mapping with strategy and resolved profile and activation delta and passed; why: selector_canary groups the supplied clauses as one enclosing predicate mapping mapping before its value is consumed.
    }


# What: define routing_profile_canary around base and artifacts; why: its direct callers call routing_profile_canary for routing profile canary and rely on this exact input and result contract.
def routing_profile_canary(base: str, artifacts: Path) -> dict:
    """Prove an active profile pin composes through a warm selector, then clear it."""
    # What: document prove an active profile pin composes in the routing_profile_canary docstring; why: introspection and maintainers read this exact docstring fragment to understand routing profile canary behavior without executing it.
    # What: compute and before from request json and base and router and status; why: value activated request json later reads and before, so routing_profile_canary must retain the computed value under that name.
    _, before = request_json(base + "/router/status")
    # What: compute prior activations from get and before and activations; why: if before get active profile model a or not later reads prior activations, so routing_profile_canary must retain the computed value under that name.
    prior_activations = before.get("activations")
    # What: gate on get and isinstance and prior activations and int and before before runtime error; why: routing_profile_canary admits runtime error only for this predicate and excludes the opposite state.
    if before.get("activeProfile") != "model-a" or not isinstance(prior_activations, int):
        # What: raise RuntimeError for the caller; why:  routing_profile_canary stops this rejected path before it can mutate state, dispatch work, or report success.
        raise RuntimeError("routing profile canary requires resident model-a")
    # What: compute raw from the named fixture input; why: raw completion canary base profile model direct later reads raw, so routing_profile_canary must retain the computed value under that name.
    raw = b""
    # What: compute listed raw from the named fixture input; why: listed raw listed request json base v1 models later reads listed raw, so routing_profile_canary must retain the computed value under that name.
    listed_raw = b""
    # What: establish the handler boundary for the protected operation; why: routing_profile_canary routes failures to the unconditional cleanup block while preserving cleanup and success flow.
    try:
        # What: compute and activated from request json and base and router and profiles and active; why: value after request json base router status later reads and activated, so routing_profile_canary must retain the computed value under that name.
        _, activated = request_json(
            # What: map the name field as coding; why: routing_profile_canary carries name through and activated into value after request json base router status.
            base + "/router/profiles/active", {"name": "coding"}, method="PUT"
        # What: complete the request_json call with method; why: routing_profile_canary groups the supplied clauses as one request_json call before its value is consumed.
        )
        # What: map the active field as coding; why: routing_profile_canary carries active through if activated != {"active": "coding"} into raise runtime error routing profile pin did not.
        if activated != {"active": "coding"}:
            # What: raise RuntimeError for the caller; why:  routing_profile_canary stops this rejected path before it can mutate state, dispatch work, or report success.
            raise RuntimeError("routing profile activation was not acknowledged")
        # What: compute listed raw and listed from request json and base and v1 and models and 10; why: artifacts routing profile models json write bytes listed raw later reads listed raw and listed, so routing_profile_canary must retain the computed value under that name.
        listed_raw, listed = request_json(base + "/v1/models", timeout=10)
        # What: compute listed ids from get and item and isinstance and dict; why: if profile model not in listed ids or later reads listed ids, so routing_profile_canary must retain the computed value under that name.
        listed_ids = {
            # What: call item.get with id; why: routing_profile_canary consumes the item.get return value while evaluating item.get("id") for item in listed.get("data", []) if isinstance(item, di.
            item.get("id") for item in listed.get("data", []) if isinstance(item, dict)
        # What: complete the listed_ids expression with listed ids item get id for item in listed get data if; why: routing_profile_canary groups the supplied clauses as one listed_ids expression before its value is consumed.
        }
        # What: gate on listed ids before runtime error; why: routing_profile_canary admits runtime error only for this predicate and excludes the opposite state.
        if "profile-model" not in listed_ids or "disabled-model" in listed_ids:
            # What: raise RuntimeError for the caller; why:  routing_profile_canary stops this rejected path before it can mutate state, dispatch work, or report success.
            raise RuntimeError("active routing profile model listing is inconsistent")
        # What: compute raw and completion from canary and base and profile model and false; why: artifacts routing profile sse write bytes raw later reads raw and completion, so routing_profile_canary must retain the computed value under that name.
        raw, completion = canary(base, "profile-model", direct=False)
        # What: compute and after from request json and base and router and status; why: value cleared request json later reads and after, so routing_profile_canary must retain the computed value under that name.
        _, after = request_json(base + "/router/status")
        # What: gate on prior activations and get and completion and after before runtime error; why: routing_profile_canary admits runtime error only for this predicate and excludes the opposite state.
        if (
            # What: call completion.get with passed; why: routing_profile_canary invokes completion.get while performing or after get active routing profile coding; the call advances that operation through its result or side effect.
            completion.get("passed") is not True
            # What: call after.get with active routing profile; why: routing_profile_canary invokes after.get while performing or after get active profile model a; the call advances that operation through its result or side effect.
            or after.get("activeRoutingProfile") != "coding"
            # What: call after.get with active profile; why: routing_profile_canary invokes after.get while performing or after get active requests; the call advances that operation through its result or side effect.
            or after.get("activeProfile") != "model-a"
            # What: call after.get with active requests; why: routing_profile_canary invokes after.get while performing or after get activations prior activations; the call advances that operation through its result or side effect.
            or after.get("activeRequests") != 0
            # What: call after.get with activations; why: routing_profile_canary consumes the after.get return value while evaluating or after.get("activations") != prior_activations.
            or after.get("activations") != prior_activations
        # What: complete the enclosing predicate with if completion get passed is not true or after get active routing profile; why: routing_profile_canary groups the supplied clauses as one enclosing predicate expression before its value is consumed.
        ):
            # What: raise RuntimeError for the caller; why:  routing_profile_canary stops this rejected path before it can mutate state, dispatch work, or report success.
            raise RuntimeError("routing profile pin did not reuse the resident selector target")
    # What: run value cleared request json on every exit path; why: routing_profile_canary performs this cleanup after success, rejection, or exception so resources and accounting cannot remain stranded.
    finally:
        # What: compute and cleared from request json and base and router and profiles and active; why: the enclosing return or state update later reads and cleared, so routing_profile_canary must retain the computed value under that name.
        _, cleared = request_json(
            # What: map the name field as the fixture input; why: routing_profile_canary carries name through and cleared into the enclosing return or state update.
            base + "/router/profiles/active", {"name": None}, method="PUT"
        # What: complete the request_json call with method; why: routing_profile_canary groups the supplied clauses as one request_json call before its value is consumed.
        )
        # What: map the active field as the fixture input; why: routing_profile_canary carries active into if cleared != {"active": None}.
        if cleared != {"active": None}:
            # What: raise RuntimeError for the caller; why:  routing_profile_canary stops this rejected path before it can mutate state, dispatch work, or report success.
            raise RuntimeError("routing profile was not cleared after its canary")
    # What: preserve the exact artifacts routing profile sse write bytes raw literal fragment; why: routing_profile_canary passes this fragment verbatim through (artifacts / "routing-profile.sse").write_bytes(raw), because changing it would alter a protocol payload, serialized fixture, or public message.
    (artifacts / "routing-profile.sse").write_bytes(raw)
    # What: preserve the exact artifacts routing profile models json write bytes listed raw literal fragment; why: routing_profile_canary passes this fragment verbatim through (artifacts / "routing-profile-models.json").write_bytes(listed_raw), because changing it would alter a protocol payload, serialized fixture, or.
    (artifacts / "routing-profile-models.json").write_bytes(listed_raw)
    # What: return; why:  the caller consumes this value as the function’s success-path result.
    return {
        # What: map the profile activated field as true; why: routing_profile_canary carries profile activated into "profileActivated": True.
        "profileActivated": True,
        # What: map the profile cleared field as true; why: routing_profile_canary carries profile cleared into "profileCleared": True.
        "profileCleared": True,
        # What: map the selector composed field as true; why: routing_profile_canary carries selector composed into "selectorComposed": True.
        "selectorComposed": True,
        # What: map the resolved profile field as model a; why: routing_profile_canary carries resolved profile into "resolvedProfile": "model-a".
        "resolvedProfile": "model-a",
        # What: map the activation delta field as 0; why: routing_profile_canary carries activation delta into "activationDelta": 0.
        "activationDelta": 0,
        # What: map the passed field as true; why: routing_profile_canary carries passed into "passed": True.
        "passed": True,
    # What: complete the enclosing predicate mapping with profile activated and profile cleared and selector composed and resolved profile and activation delta; why: routing_profile_canary groups the supplied clauses as one enclosing predicate mapping mapping before its value is consumed.
    }


# What: define capture_hardware around base and artifacts and label; why: its direct callers call capture_hardware for capture hardware and rely on this exact input and result contract.
def capture_hardware(base: str, artifacts: Path, label: str) -> dict:
    """Keep per-trial process and memory observations in the private artifact set."""
    # What: document keep per trial process and memory observations in the capture_hardware docstring; why: introspection and maintainers read this exact docstring fragment to understand capture hardware behavior without executing it.
    # What: compute raw and hardware from request json and base and router and hardware; why: artifacts f label hardware json write bytes raw later reads raw and hardware, so capture_hardware must retain the computed value under that name.
    raw, hardware = request_json(base + "/router/hardware")
    # What: compute engine from get and hardware and engine; why: if not isinstance engine dict or later reads engine, so capture_hardware must retain the computed value under that name.
    engine = hardware.get("engine")
    # What: compute memory from get and hardware and memory; why: if not isinstance engine dict or later reads memory, so capture_hardware must retain the computed value under that name.
    memory = hardware.get("memory")
    # What: gate on isinstance and engine and dict and memory before runtime error; why: capture_hardware admits runtime error only for this predicate and excludes the opposite state.
    if not isinstance(engine, dict) or not isinstance(memory, dict):
        # What: raise RuntimeError for the caller; why:  capture_hardware stops this rejected path before it can mutate state, dispatch work, or report success.
        raise RuntimeError("router hardware observation has an invalid shape")  # noqa: TRY004 -- malformed remote telemetry is an operational failure.
    # What: gate on get and isinstance and int and engine before runtime error; why: capture_hardware admits runtime error only for this predicate and excludes the opposite state.
    if (
        # What: call engine.get with running; why: capture_hardware invokes engine.get while performing or not isinstance engine get pid int; the call advances that operation through its result or side effect.
        not engine.get("running")
        # What: call isinstance with get and engine and pid and int; why: capture_hardware invokes isinstance while performing or engine pid; the call advances that operation through its result or side effect.
        or not isinstance(engine.get("pid"), int)
        # What: apply the or engine pid portion of the enclosing predicate; why: this clause remains in capture_hardware\'s enclosing expression so its grouping and evaluation order stay intact.
        or engine["pid"] <= 0
        # What: call isinstance with get and engine and port and int; why: capture_hardware invokes isinstance while performing or not engine port; the call advances that operation through its result or side effect.
        or not isinstance(engine.get("port"), int)
        # What: apply the or not engine port portion of the enclosing predicate; why: this clause remains in capture_hardware\'s enclosing expression so its grouping and evaluation order stay intact.
        or not 1 <= engine["port"] <= 65535
    # What: complete the enclosing predicate with if not engine get running or not isinstance engine get pid; why: capture_hardware groups the supplied clauses as one enclosing predicate expression before its value is consumed.
    ):
        # What: raise RuntimeError for the caller; why:  capture_hardware stops this rejected path before it can mutate state, dispatch work, or report success.
        raise RuntimeError("router hardware observation does not identify a running engine")
    # What: gate on all and isinstance and int and key and get before runtime error; why: capture_hardware admits runtime error only for this predicate and excludes the opposite state.
    if not all(isinstance(memory.get(key), int) for key in ("ramBytes", "vramBytes")):
        # What: raise RuntimeError for the caller; why:  capture_hardware stops this rejected path before it can mutate state, dispatch work, or report success.
        raise RuntimeError("router hardware observation lacks byte measurements")
    # What: gate on get and memory before runtime error; why: capture_hardware admits runtime error only for this predicate and excludes the opposite state.
    if memory.get("ramAvailable") is not True or memory.get("vramAvailable") is not True:
        # What: raise RuntimeError for the caller; why:  capture_hardware stops this rejected path before it can mutate state, dispatch work, or report success.
        raise RuntimeError("router hardware observation contains unavailable memory measurements")
    # What: gate on memory before runtime error; why: capture_hardware admits runtime error only for this predicate and excludes the opposite state.
    if memory["ramBytes"] <= 0 or memory["vramBytes"] <= 0:
        # What: raise RuntimeError for the caller; why:  capture_hardware stops this rejected path before it can mutate state, dispatch work, or report success.
        raise RuntimeError("router hardware observation contains non-positive memory measurements")
    # What: gate on all and key and isinstance and str and memory before runtime error; why: capture_hardware admits runtime error only for this predicate and excludes the opposite state.
    if not all(isinstance(memory.get(key), str) and memory[key] for key in ("ramSource", "vramSource")):
        # What: raise RuntimeError for the caller; why:  capture_hardware stops this rejected path before it can mutate state, dispatch work, or report success.
        raise RuntimeError("router hardware observation lacks memory measurement sources")
    # What: preserve the exact artifacts f label hardware json write bytes raw literal fragment; why: capture_hardware passes this fragment verbatim through (artifacts / f"{label}.hardware.json").write_bytes(raw), because changing it would alter a protocol payload, serialized fixture, or public message.
    (artifacts / f"{label}.hardware.json").write_bytes(raw)
    # What: return hardware from capture_hardware; why: capture_hardware exposes hardware so its caller can continue with the function\'s computed outcome.
    return hardware


# What: define validate_re_adoption around before and after and router; why: its direct callers call validate_re_adoption for validate re adoption and rely on this exact input and result contract.
def validate_re_adoption(before: dict, after: dict, router: dict) -> dict:
    """Validate that a replacement daemon bound, rather than replaced, one engine."""
    # What: document validate that a replacement daemon bound in the validate_re_adoption docstring; why: introspection and maintainers read this exact docstring fragment to understand validate re adoption behavior without executing it.
    # What: compute old pid and old port from get and before and pid and port; why: or not isinstance old pid int or later reads old pid and old port, so validate_re_adoption must retain the computed value under that name.
    old_pid, old_port = before.get("pid"), before.get("port")
    # What: gate on old pid and get and isinstance and int and old port before runtime error; why: validate_re_adoption admits runtime error only for this predicate and excludes the opposite state.
    if (
        # What: call before.get with running; why: validate_re_adoption invokes before.get while performing or not isinstance old pid int or; the call advances that operation through its result or side effect.
        not before.get("running")
        # What: call isinstance with old pid and int; why: validate_re_adoption invokes isinstance while performing or not isinstance old port int or; the call advances that operation through its result or side effect.
        or not isinstance(old_pid, int) or old_pid <= 0
        # What: call isinstance with old port and int; why: validate_re_adoption consumes the isinstance return value while evaluating or not isinstance(old_port, int) or not 1 <= old_port <= 65535.
        or not isinstance(old_port, int) or not 1 <= old_port <= 65535
    # What: complete the enclosing predicate with if not before get running or not isinstance old pid int; why: validate_re_adoption groups the supplied clauses as one enclosing predicate expression before its value is consumed.
    ):
        # What: raise RuntimeError for the caller; why:  validate_re_adoption stops this rejected path before it can mutate state, dispatch work, or report success.
        raise RuntimeError("pre-restart engine identity is invalid")
    # What: gate on old pid and old port and get and after and router before runtime error; why: validate_re_adoption admits runtime error only for this predicate and excludes the opposite state.
    if (
        # What: call after.get with pid; why: validate_re_adoption invokes after.get while performing or after get port old port; the call advances that operation through its result or side effect.
        after.get("pid") != old_pid
        # What: call after.get with port; why: validate_re_adoption invokes after.get while performing or after get adopted is not; the call advances that operation through its result or side effect.
        or after.get("port") != old_port
        # What: call after.get with adopted; why: validate_re_adoption invokes after.get while performing or router get active profile model a; the call advances that operation through its result or side effect.
        or after.get("adopted") is not True
        # What: call router.get with active profile; why: validate_re_adoption invokes router.get while performing or router get active identity matches engine is not; the call advances that operation through its result or side effect.
        or router.get("activeProfile") != "model-a"
        # What: call router.get with active identity matches engine; why: validate_re_adoption invokes router.get while performing or router get activations; the call advances that operation through its result or side effect.
        or router.get("activeIdentityMatchesEngine") is not True
        # What: call router.get with activations; why: validate_re_adoption consumes the router.get return value while evaluating or router.get("activations") != 0.
        or router.get("activations") != 0
    # What: complete the enclosing predicate with if after get pid differs from old pid or after get port; why: validate_re_adoption groups the supplied clauses as one enclosing predicate expression before its value is consumed.
    ):
        # What: raise RuntimeError for the caller; why:  validate_re_adoption stops this rejected path before it can mutate state, dispatch work, or report success.
        raise RuntimeError("replacement daemon did not bind the exact adopted residency")
    # What: return profile and same pid and same port and manager adopted and activation delta from validate_re_adoption; why: validate_re_adoption exposes profile and same pid and same port and manager adopted and activation delta so its caller can continue with the function\'s computed outcome.
    return {
        # What: map the profile field as model a; why: validate_re_adoption carries profile into "profile": "model-a", "samePid": True, "samePort": True.
        "profile": "model-a", "samePid": True, "samePort": True,
        # What: map the manager adopted field as true; why: validate_re_adoption carries manager adopted into "managerAdopted": True, "activationDelta": 0.
        "managerAdopted": True, "activationDelta": 0,
    # What: complete the enclosing predicate mapping with profile and same pid and same port and manager adopted and activation delta; why: validate_re_adoption groups the supplied clauses as one enclosing predicate mapping mapping before its value is consumed.
    }


# What: define require_listener_closed around port; why: its direct callers call require_listener_closed for require listener closed and rely on this exact input and result contract.
def require_listener_closed(port: int) -> None:
    """Fail the qualification if a temporary engine listener survived cleanup."""
    # What: document fail the qualification if a temporary in the require_listener_closed docstring; why: introspection and maintainers read this exact docstring fragment to understand require listener closed behavior without executing it.
    # What: enter the socket.socket managed context before connection settimeout; why: require_listener_closed releases this resource or lock after connection settimeout on both success and failure paths.
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as connection:
        # What: call connection.settimeout with 1; why: require_listener_closed invokes connection.settimeout while performing if connection connect ex port; the call advances that operation through its result or side effect.
        connection.settimeout(1)
        # What: gate on connect ex and connection and port before runtime error; why: require_listener_closed admits runtime error only for this predicate and excludes the opposite state.
        if connection.connect_ex(("127.0.0.1", port)) == 0:
            # What: raise RuntimeError for the caller; why: require_listener_closed stops this rejected path before it can mutate state, dispatch work, or report success.
            raise RuntimeError("temporary engine listener remains reachable after cleanup")


# What: define require_listener_open around port; why: its direct callers call require_listener_open for require listener open and rely on this exact input and result contract.
def require_listener_open(port: int) -> None:
    """Require a detached test-owned engine to remain reachable for re-adoption."""
    # What: document require a detached test owned engine to in the require_listener_open docstring; why: introspection and maintainers read this exact docstring fragment to understand require listener open behavior without executing it.
    # What: enter the socket.socket managed context before connection settimeout; why: require_listener_open releases this resource or lock after connection settimeout on both success and failure paths.
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as connection:
        # What: call connection.settimeout with 1; why: require_listener_open invokes connection.settimeout while performing if connection connect ex port; the call advances that operation through its result or side effect.
        connection.settimeout(1)
        # What: gate on connect ex and connection and port before runtime error; why: require_listener_open admits runtime error only for this predicate and excludes the opposite state.
        if connection.connect_ex(("127.0.0.1", port)) != 0:
            # What: raise RuntimeError for the caller; why: require_listener_open stops this rejected path before it can mutate state, dispatch work, or report success.
            raise RuntimeError("detached engine listener did not survive daemon restart")


# What: define stop_detached_engine around pid and port; why: its direct callers call stop_detached_engine for stop detached engine and rely on this exact input and result contract.
def stop_detached_engine(pid: int, port: int) -> None:
    """Best-effort cleanup for the exact test-owned engine during a restart gap."""
    # What: document best effort cleanup for the exact test owned in the stop_detached_engine docstring; why: introspection and maintainers read this exact docstring fragment to understand stop detached engine behavior without executing it.
    # What: establish the handler boundary for the protected operation; why: stop_detached_engine routes failures to process lookup error while preserving cleanup and success flow.
    try:
        # What: call os.killpg with pid and sigterm and signal; why: stop_detached_engine invokes os.killpg while performing except process lookup error; the call advances that operation through its result or side effect.
        os.killpg(pid, signal.SIGTERM)
    # What: handle process lookup error by return; why: stop_detached_engine converts that failure into this concrete recovery, response, or cleanup behavior.
    except ProcessLookupError:
        # What: return no value from stop_detached_engine; why: stop_detached_engine returns no value to callers that depend on its completed result.
        return
    # What: compute deadline from monotonic and time and 15; why: while time monotonic deadline later reads deadline, so stop_detached_engine must retain the computed value under that name.
    deadline = time.monotonic() + 15
    # What: iterate across deadline and monotonic and time to perform runtime error and require listener closed and port and sleep and time; why: stop_detached_engine repeats the body only while or for the loop header admits an iteration.
    while time.monotonic() < deadline:
        # What: establish the handler boundary for the protected operation; why: stop_detached_engine routes failures to runtime error while preserving cleanup and success flow.
        try:
            # What: call require_listener_closed with port; why: stop_detached_engine invokes require_listener_closed while performing return; the call advances that operation through its result or side effect.
            require_listener_closed(port)
            # What: return no value from stop_detached_engine; why: stop_detached_engine returns no value to callers that depend on its completed result.
            return
        # What: handle runtime error by time sleep 0 1; why: stop_detached_engine converts that failure into this concrete recovery, response, or cleanup behavior.
        except RuntimeError:
            # What: call time.sleep with 0 1; why: stop_detached_engine invokes time.sleep while performing try; the call advances that operation through its result or side effect.
            time.sleep(0.1)
    # What: establish the handler boundary for the protected operation; why: stop_detached_engine routes failures to process lookup error while preserving cleanup and success flow.
    try:
        # What: call os.killpg with pid and sigkill and signal; why: stop_detached_engine invokes os.killpg while performing except process lookup error; the call advances that operation through its result or side effect.
        os.killpg(pid, signal.SIGKILL)
    # What: handle process lookup error by pass; why: stop_detached_engine converts that failure into this concrete recovery, response, or cleanup behavior.
    except ProcessLookupError:
        # What: ignore the anticipated exception handled by this branch; why: stop_detached_engine continues its retry or cleanup path instead of re-raising that transient failure.
        pass
    # What: compute deadline from monotonic and time and 5; why: while time monotonic deadline later reads deadline, so stop_detached_engine must retain the computed value under that name.
    deadline = time.monotonic() + 5
    # What: iterate across deadline and monotonic and time to perform runtime error and require listener closed and port and sleep and time; why: stop_detached_engine repeats the body only while or for the loop header admits an iteration.
    while time.monotonic() < deadline:
        # What: establish the handler boundary for the protected operation; why: stop_detached_engine routes failures to runtime error while preserving cleanup and success flow.
        try:
            # What: call require_listener_closed with port; why: stop_detached_engine invokes require_listener_closed while performing return; the call advances that operation through its result or side effect.
            require_listener_closed(port)
            # What: return no value from stop_detached_engine; why: stop_detached_engine returns no value to callers that depend on its completed result.
            return
        # What: handle runtime error by time sleep 0 1; why: stop_detached_engine converts that failure into this concrete recovery, response, or cleanup behavior.
        except RuntimeError:
            # What: call time.sleep with 0 1; why: stop_detached_engine invokes time.sleep while performing raise runtime error detached test owned engine survived; the call advances that operation through its result or side effect.
            time.sleep(0.1)
    # What: raise RuntimeError for the caller; why: stop_detached_engine stops this rejected path before it can mutate state, dispatch work, or report success.
    raise RuntimeError("detached test-owned engine survived cleanup")


# What: discover the exact engine process currently owned by the temporary daemon; why: failure cleanup must not leak a model process that consumes unified memory after the daemon exits.
def running_engine_identity(base: str) -> tuple[int, int] | None:
    # What: query the daemon's authoritative engine status; why: process cleanup must use the manager-recorded PID and listener rather than broad process matching.
    try:
        # What: retain the decoded engine status response; why: validated running state, PID, and port are all required before a process can be treated as test-owned.
        _, engine = request_json(base + "/engine/status", timeout=10)
    # What: treat an unavailable daemon status endpoint as no capturable engine; why: cleanup continues through existing process-group and detached-engine safeguards.
    except (OSError, ValueError, urllib.error.HTTPError):
        # What: return no identity when ownership cannot be proven; why: cleanup must never signal an unverified process.
        return None
    # What: extract the manager-recorded process identity fields; why: both values are needed to terminate the process group and verify listener closure.
    pid, port = engine.get("pid"), engine.get("port")
    # What: accept only a running engine with valid integer identity fields; why: malformed or idle status must not be converted into an unsafe signal target.
    if engine.get("running") is True and isinstance(pid, int) and isinstance(port, int):
        # What: return the exact test-owned process identity; why: the caller can perform bounded targeted cleanup on every exit path.
        return pid, port
    # What: return no identity for an idle or invalid engine status; why: there is no proven process for cleanup to stop.
    return None


# What: define reload_conflict_canary around base and catalog path and model a and model b and api key; why: its direct callers call reload_conflict_canary for reload conflict canary and rely on this exact input and result contract.
def reload_conflict_canary(
    # What: declare the base input for reload_conflict_canary; why: reload_conflict_canary consumes base during value status request json base router status, so callers must bind it with the other signature inputs.
    base: str, catalog_path: Path, model_a: str, model_b: str, *, api_key: str | None = None
# What: complete the enclosing predicate with dict; why: reload_conflict_canary groups the supplied clauses as one enclosing predicate expression before its value is consumed.
) -> dict:
    """Prove an active profile's scheduler policy cannot change under its engine."""
    # What: document prove an active profile s scheduler in the reload_conflict_canary docstring; why: introspection and maintainers read this exact docstring fragment to understand reload conflict canary behavior without executing it.
    # What: call catalog_path.write_text with native catalog text and model a and model b and api key and 1; why: reload_conflict_canary invokes catalog_path.write_text while performing native catalog text model a model b model a priority api key api key; the call advances that operation through its result or side effect.
    catalog_path.write_text(
        # What: supply model a priority to native_catalog_text; why: reload_conflict_canary binds this 1 value to native_catalog_text's model a priority input.
        native_catalog_text(model_a, model_b, model_a_priority=1, api_key=api_key),
        # What: preserve the exact encoding utf 8 literal fragment; why: reload_conflict_canary passes this fragment verbatim through encoding="utf-8", because changing it would alter a protocol payload, serialized fixture, or public message.
        encoding="utf-8",
    # What: complete the catalog_path.write_text call with encoding; why: reload_conflict_canary groups the supplied clauses as one catalog_path.write_text call before its value is consumed.
    )
    # What: establish the handler boundary for the protected operation; why: reload_conflict_canary routes failures to httperror and error and urllib while preserving cleanup and success flow.
    try:
        # What: preserve the exact request json base router reload timeout literal fragment; why: reload_conflict_canary passes this fragment verbatim through request_json(base + "/router/reload", {}, timeout=30), because changing it would alter a protocol payload, serialized fixture, or public message.
        request_json(base + "/router/reload", {}, timeout=30)
    # What: handle httperror and error and urllib by if exc code differs from 409; why: reload_conflict_canary converts that failure into this concrete recovery, response, or cleanup behavior.
    except urllib.error.HTTPError as exc:
        # What: gate on code and exc before exc and runtime error; why: reload_conflict_canary admits exc and runtime error only for this predicate and excludes the opposite state.
        if exc.code != 409:
            # What: raise RuntimeError for the caller; why:  reload_conflict_canary stops this rejected path before it can mutate state, dispatch work, or report success.
            raise RuntimeError("active catalog conflict returned the wrong status") from exc
    # What: select the remaining branch that performs raise runtime error active catalog scheduler redefinition; why: reload_conflict_canary covers the state excluded by the preceding predicate without conflating the two outcomes.
    else:
        # What: raise RuntimeError for the caller; why:  reload_conflict_canary stops this rejected path before it can mutate state, dispatch work, or report success.
        raise RuntimeError("active catalog scheduler redefinition was accepted")
    # What: compute and status from request json and base and router and status and 30; why: the enclosing return or state update later reads and status, so reload_conflict_canary must retain the computed value under that name.
    _, status = request_json(base + "/router/status", timeout=30)
    # What: gate on get and status before runtime error; why: reload_conflict_canary admits runtime error only for this predicate and excludes the opposite state.
    if status.get("activeProfile") != "model-a" or status.get("activeIdentityMatchesEngine") is not True:
        # What: raise RuntimeError for the caller; why:  reload_conflict_canary stops this rejected path before it can mutate state, dispatch work, or report success.
        raise RuntimeError("rejected catalog replacement changed active engine identity")
    # What: return active profile and rejected status and active identity preserved and passed and model a from reload_conflict_canary; why: qualify_native_router needs this line to preserve the surrounding expression or collection structure.
    return {
        # What: map the active profile field as model a; why: reload_conflict_canary carries active profile into "activeProfile": "model-a".
        "activeProfile": "model-a",
        # What: map the rejected status field as 409; why: reload_conflict_canary carries rejected status into "rejectedStatus": 409.
        "rejectedStatus": 409,
        # What: map the active identity preserved field as true; why: reload_conflict_canary carries active identity preserved into "activeIdentityPreserved": True.
        "activeIdentityPreserved": True,
        # What: map the passed field as true; why: reload_conflict_canary carries passed into "passed": True.
        "passed": True,
    # What: complete the enclosing predicate mapping with active profile and rejected status and active identity preserved and passed; why: reload_conflict_canary groups the supplied clauses as one enclosing predicate mapping mapping before its value is consumed.
    }


# What: define failed_switch_canary around base and model and restored model; why: its direct callers call failed_switch_canary for failed switch canary and rely on this exact input and result contract.
def failed_switch_canary(base: str, model: str, restored_model: str) -> tuple[bytes, bytes, dict]:
    """Require a failed disposable load to restore the prior resident engine."""
    # What: document require a failed disposable load to in the failed_switch_canary docstring; why: introspection and maintainers read this exact docstring fragment to understand failed switch canary behavior without executing it.
    # What: compute and before from request json and base and router and status; why: value pending before request json base accounting pending later reads and before, so failed_switch_canary must retain the computed value under that name.
    _, before = request_json(base + "/router/status")
    # What: compute and pending before from request json and base and accounting and pending; why: value after request json base router status later reads and pending before, so failed_switch_canary must retain the computed value under that name.
    _, pending_before = request_json(base + "/accounting/pending")
    # What: compute receipts before from get and pending before and receipts; why: if not isinstance receipts before list later reads receipts before, so failed_switch_canary must retain the computed value under that name.
    receipts_before = pending_before.get("receipts")
    # What: gate on isinstance and receipts before and list before runtime error; why: failed_switch_canary admits runtime error only for this predicate and excludes the opposite state.
    if not isinstance(receipts_before, list):
        # What: raise RuntimeError for the caller; why:  failed_switch_canary stops this rejected path before it can mutate state, dispatch work, or report success.
        raise RuntimeError("accounting outbox response has an invalid shape")  # noqa: TRY004 -- malformed remote state is an operational failure.
    # What: compute before ids from get and receipt and receipts before and isinstance; why: new receipts after ids before ids later reads before ids, so failed_switch_canary must retain the computed value under that name.
    before_ids = {
        # What: call receipt.get with receipt id; why:  failed_switch_canary invokes receipt.get while performing if isinstance receipt dict and isinstance; the call advances that operation through its result or side effect.
        receipt.get("receiptId") for receipt in receipts_before
        # What: call isinstance with receipt and dict; why: failed_switch_canary consumes the isinstance return value while evaluating if isinstance(receipt, dict) and isinstance(receipt.get("receiptId"), st.
        if isinstance(receipt, dict) and isinstance(receipt.get("receiptId"), str)
    # What: complete the before_ids expression with before ids receipt get receipt id for receipt in receipts before if isinstance; why: failed_switch_canary groups the supplied clauses as one before_ids expression before its value is consumed.
    }
    # What: compute prior failures from get and before and activation failures; why: or not isinstance prior failures int later reads prior failures, so failed_switch_canary must retain the computed value under that name.
    prior_failures = before.get("activationFailures")
    # What: gate on restored model and get and isinstance and prior failures and int before runtime error; why: failed_switch_canary admits runtime error only for this predicate and excludes the opposite state.
    if (
        # What: call before.get with active profile; why: failed_switch_canary invokes before.get while performing or before get active identity matches engine is not; the call advances that operation through its result or side effect.
        before.get("activeProfile") != restored_model
        # What: call before.get with active identity matches engine; why: failed_switch_canary invokes before.get while performing or not isinstance prior failures int; the call advances that operation through its result or side effect.
        or before.get("activeIdentityMatchesEngine") is not True
        # What: call isinstance with prior failures and int; why: failed_switch_canary consumes the isinstance return value while evaluating or not isinstance(prior_failures, int).
        or not isinstance(prior_failures, int)
    # What: complete the enclosing predicate with if before get active profile differs from restored model or before get active identity matches engine; why: failed_switch_canary groups the supplied clauses as one enclosing predicate expression before its value is consumed.
    ):
        # What: raise RuntimeError for the caller; why:  failed_switch_canary stops this rejected path before it can mutate state, dispatch work, or report success.
        raise RuntimeError("failed-switch qualification requires an exact healthy resident")
    # What: compute failure raw from the named fixture input; why: failure raw exc read later reads failure raw, so failed_switch_canary must retain the computed value under that name.
    failure_raw = b""
    # What: establish the handler boundary for the protected operation; why: failed_switch_canary routes failures to httperror and error and urllib while preserving cleanup and success flow.
    try:
        # What: map the name field as model; why: failed_switch_canary carries name into request_json(base + "/router/load", {"name": model}, timeout=90).
        request_json(base + "/router/load", {"name": model}, timeout=90)
    # What: handle httperror and error and urllib by failure raw exc read 1024 1024 1; why: failed_switch_canary converts that failure into this concrete recovery, response, or cleanup behavior.
    except urllib.error.HTTPError as exc:
        # What: compute failure raw from read and exc and 1 and 1024 and 1024; why: if exc code or len failure raw later reads failure raw, so failed_switch_canary must retain the computed value under that name.
        failure_raw = exc.read(1024 * 1024 + 1)
        # What: gate on code and exc and len and failure raw before exc and runtime error; why: failed_switch_canary admits exc and runtime error only for this predicate and excludes the opposite state.
        if exc.code != 503 or len(failure_raw) > 1024 * 1024:
            # What: raise RuntimeError for the caller; why:  failed_switch_canary stops this rejected path before it can mutate state, dispatch work, or report success.
            raise RuntimeError("failed replacement returned an invalid bounded response") from exc
    # What: select the remaining branch that performs raise runtime error disposable invalid model unexpectedly; why: failed_switch_canary covers the state excluded by the preceding predicate without conflating the two outcomes.
    else:
        # What: raise RuntimeError for the caller; why:  failed_switch_canary stops this rejected path before it can mutate state, dispatch work, or report success.
        raise RuntimeError("disposable invalid model unexpectedly activated")
    # What: establish the handler boundary for the protected operation; why: failed_switch_canary routes failures to unicode decode error and jsondecode error and json while preserving cleanup and success flow.
    try:
        # What: compute failure from loads and failure raw and json; why: error failure get error if isinstance failure later reads failure, so failed_switch_canary must retain the computed value under that name.
        failure = json.loads(failure_raw)
    # What: handle unicode decode error and jsondecode error and json by raise runtime error failed replacement response was not; why: failed_switch_canary converts that failure into this concrete recovery, response, or cleanup behavior.
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        # What: raise RuntimeError for the caller; why:  failed_switch_canary stops this rejected path before it can mutate state, dispatch work, or report success.
        raise RuntimeError("failed replacement response was not JSON") from exc
    # What: compute error from isinstance and failure and dict and get and error; why: if not isinstance error dict or later reads error, so failed_switch_canary must retain the computed value under that name.
    error = failure.get("error") if isinstance(failure, dict) else None
    # What: compute recovery from isinstance and failure and dict and get and recovery; why: if not isinstance recovery dict or later reads recovery, so failed_switch_canary must retain the computed value under that name.
    recovery = failure.get("recovery") if isinstance(failure, dict) else None
    # What: gate on isinstance and error and dict and get before runtime error; why: failed_switch_canary admits runtime error only for this predicate and excludes the opposite state.
    if not isinstance(error, dict) or error.get("type") not in {"engine_not_ready", "switch_launch_failed"}:
        # What: raise RuntimeError for the caller; why:  failed_switch_canary stops this rejected path before it can mutate state, dispatch work, or report success.
        raise RuntimeError("failed replacement did not report a lifecycle failure")
    # What: gate on isinstance and recovery and dict and get before runtime error; why: failed_switch_canary admits runtime error only for this predicate and excludes the opposite state.
    if not isinstance(recovery, dict) or recovery.get("launched") is not True:
        # What: raise RuntimeError for the caller; why:  failed_switch_canary stops this rejected path before it can mutate state, dispatch work, or report success.
        raise RuntimeError("failed replacement did not report successful rollback launch")
    # What: compute and after from request json and base and router and status and 30; why: value pending after request json base accounting pending later reads and after, so failed_switch_canary must retain the computed value under that name.
    _, after = request_json(base + "/router/status", timeout=30)
    # What: gate on restored model and get and prior failures and after before runtime error; why: failed_switch_canary admits runtime error only for this predicate and excludes the opposite state.
    if (
        # What: call after.get with active profile; why: failed_switch_canary invokes after.get while performing or after get active identity matches engine is not; the call advances that operation through its result or side effect.
        after.get("activeProfile") != restored_model
        # What: call after.get with active identity matches engine; why: failed_switch_canary invokes after.get while performing or after get active requests; the call advances that operation through its result or side effect.
        or after.get("activeIdentityMatchesEngine") is not True
        # What: call after.get with active requests; why: failed_switch_canary invokes after.get while performing or after get activation failures prior failures; the call advances that operation through its result or side effect.
        or after.get("activeRequests") != 0
        # What: call after.get with activation failures; why: failed_switch_canary consumes the after.get return value while evaluating or after.get("activationFailures") != prior_failures + 1.
        or after.get("activationFailures") != prior_failures + 1
    # What: complete the enclosing predicate with if after get active profile differs from restored model or after get active identity matches engine; why: failed_switch_canary groups the supplied clauses as one enclosing predicate expression before its value is consumed.
    ):
        # What: raise RuntimeError for the caller; why:  failed_switch_canary stops this rejected path before it can mutate state, dispatch work, or report success.
        raise RuntimeError("failed replacement did not restore exact idle residency")
    # What: compute and pending after from request json and base and accounting and pending; why: the enclosing return or state update later reads and pending after, so failed_switch_canary must retain the computed value under that name.
    _, pending_after = request_json(base + "/accounting/pending")
    # What: compute receipts after from get and pending after and receipts; why: if not isinstance receipts after list later reads receipts after, so failed_switch_canary must retain the computed value under that name.
    receipts_after = pending_after.get("receipts")
    # What: gate on isinstance and receipts after and list before runtime error; why: failed_switch_canary admits runtime error only for this predicate and excludes the opposite state.
    if not isinstance(receipts_after, list):
        # What: raise RuntimeError for the caller; why:  failed_switch_canary stops this rejected path before it can mutate state, dispatch work, or report success.
        raise RuntimeError("post-failure accounting outbox response has an invalid shape")  # noqa: TRY004 -- malformed remote state is an operational failure.
    # What: compute after ids from get and receipt and receipts after and isinstance; why: new receipts after ids before ids later reads after ids, so failed_switch_canary must retain the computed value under that name.
    after_ids = {
        # What: call receipt.get with receipt id; why:  failed_switch_canary invokes receipt.get while performing if isinstance receipt dict and isinstance; the call advances that operation through its result or side effect.
        receipt.get("receiptId") for receipt in receipts_after
        # What: call isinstance with receipt and dict; why: failed_switch_canary consumes the isinstance return value while evaluating if isinstance(receipt, dict) and isinstance(receipt.get("receiptId"), st.
        if isinstance(receipt, dict) and isinstance(receipt.get("receiptId"), str)
    # What: complete the after_ids expression with after ids receipt get receipt id for receipt in receipts after if isinstance; why: failed_switch_canary groups the supplied clauses as one after_ids expression before its value is consumed.
    }
    # What: compute new receipts from after ids and before ids; why: if not new receipts later reads new receipts, so failed_switch_canary must retain the computed value under that name.
    new_receipts = after_ids - before_ids
    # What: gate on new receipts before runtime error; why: failed_switch_canary admits runtime error only for this predicate and excludes the opposite state.
    if not new_receipts:
        # What: raise RuntimeError for the caller; why:  failed_switch_canary stops this rejected path before it can mutate state, dispatch work, or report success.
        raise RuntimeError("failed switch produced no new durable accounting receipt")
    # What: read the restored engine status after rollback launch; why: router identity can be restored before the replacement process is actually ready to serve traffic.
    _, restored_engine = request_json(base + "/engine/status", timeout=30)
    # What: extract the restored engine listener port; why: readiness must be proven against the concrete replacement process rather than inferred from router metadata.
    restored_port = restored_engine.get("port")
    # What: reject a missing or invalid restored listener; why: waiting without an exact local port could probe the wrong process and create false recovery evidence.
    if restored_engine.get("running") is not True or not isinstance(restored_port, int):
        # What: stop qualification when rollback has no concrete running listener; why: a metadata-only rollback is not a usable restored service.
        raise RuntimeError("failed replacement rollback has no running engine listener")
    # What: wait for the restored process readiness endpoint; why: a launched process may still be loading model weights when router state already names it active.
    wait_json(f"http://127.0.0.1:{restored_port}/ready", seconds=600)
    # What: compute restored raw and restored from canary and base and restored model and false; why: return failure raw restored raw later reads restored raw and restored, so failed_switch_canary must retain the computed value under that name.
    restored_raw, restored = canary(base, restored_model, direct=False)
    # What: return failure raw and restored raw and model and restored model from failed_switch_canary; why: failed_switch_canary exposes failure raw and restored raw and model and restored model so its caller can continue with the function\'s computed outcome.
    return failure_raw, restored_raw, {
        # What: map the failed profile field as model; why: failed_switch_canary carries failed profile into "failedProfile": model.
        "failedProfile": model,
        # What: map the restored profile field as restored model; why: failed_switch_canary carries restored profile into "restoredProfile": restored_model.
        "restoredProfile": restored_model,
        # What: map the failure type field as error and type; why: failed_switch_canary carries failure type into "failureType": error["type"].
        "failureType": error["type"],
        # What: map the rollback launched field as true; why: failed_switch_canary carries rollback launched into "rollbackLaunched": True.
        "rollbackLaunched": True,
        # What: map the activation failure incremented field as true; why: failed_switch_canary carries activation failure incremented into "activationFailureIncremented": True.
        "activationFailureIncremented": True,
        # What: map the new accounting receipt count field as len and new receipts; why: failed_switch_canary carries new accounting receipt count into "newAccountingReceiptCount": len(new_receipts).
        "newAccountingReceiptCount": len(new_receipts),
        # What: map the restored completion passed field as get and restored and true and passed; why: failed_switch_canary carries restored completion passed into "restoredCompletionPassed": restored.get("passed") is True.
        "restoredCompletionPassed": restored.get("passed") is True,
        # What: map the passed field as get and restored and true and passed; why: failed_switch_canary carries passed into "passed": restored.get("passed") is True.
        "passed": restored.get("passed") is True,
    # What: complete the enclosing predicate collection with failure raw and restored raw and model and restored model and error and len; why: failed_switch_canary groups the supplied clauses as one enclosing predicate collection collection before its value is consumed.
    }


# What: define persistent_capacity_canary around base and catalog path and model a and model b and api key; why: its direct callers call persistent_capacity_canary for persistent capacity canary and rely on this exact input and result contract.
def persistent_capacity_canary(
    # What: declare the base input for persistent_capacity_canary; why: persistent_capacity_canary consumes base during value loaded a request json base router load, so callers must bind it with the other signature inputs.
    base: str, catalog_path: Path, model_a: str, model_b: str, *, api_key: str | None = None
# What: complete the enclosing predicate collection with bytes and dict; why: persistent_capacity_canary groups the supplied clauses as one enclosing predicate collection collection before its value is consumed.
) -> tuple[bytes, dict]:
    """Prove a singleton persistent group reserves the sole resident slot."""
    # What: document prove a singleton persistent group reserves in the persistent_capacity_canary docstring; why: introspection and maintainers read this exact docstring fragment to understand persistent capacity canary behavior without executing it.
    # What: gate on get and request json and base before runtime error; why:  persistent_capacity_canary admits runtime error only for this predicate and excludes the opposite state.
    if request_json(base + "/router/unload", {}, timeout=45)[1].get("unloaded") is not True:
        # What: raise RuntimeError for the caller; why:  persistent_capacity_canary stops this rejected path before it can mutate state, dispatch work, or report success.
        raise RuntimeError("could not unload before persistent capacity qualification")
    # What: call catalog_path.write_text; why: qualify_native_router needs this line to preserve the surrounding expression or collection structure.
    catalog_path.write_text(
        # What: supply persistent a to native_catalog_text; why: persistent_capacity_canary binds this true value to native_catalog_text's persistent a input.
        native_catalog_text(model_a, model_b, persistent_a=True, api_key=api_key),
        # What: preserve the exact encoding utf 8 literal fragment; why: persistent_capacity_canary passes this fragment verbatim through encoding="utf-8", because changing it would alter a protocol payload, serialized fixture, or public message.
        encoding="utf-8",
    # What: complete the catalog_path.write_text call with encoding; why: persistent_capacity_canary groups the supplied clauses as one catalog_path.write_text call before its value is consumed.
    )
    # What: gate on get and request json and base before runtime error; why:  persistent_capacity_canary admits runtime error only for this predicate and excludes the opposite state.
    if request_json(base + "/router/reload", {}, timeout=30)[1].get("reloaded") is not True:
        # What: raise RuntimeError for the caller; why:  persistent_capacity_canary stops this rejected path before it can mutate state, dispatch work, or report success.
        raise RuntimeError("persistent catalog reload was not acknowledged")
    # What: map the name field as model a; why: persistent_capacity_canary carries name through and loaded a into value still a request json base router status.
    _, loaded_a = request_json(base + "/router/load", {"name": "model-a"}, timeout=660)
    # What: compute router a and pid a from get and loaded a and router and pid; why: or not isinstance router a dict or later reads router a and pid a, so persistent_capacity_canary must retain the computed value under that name.
    router_a, pid_a = loaded_a.get("router"), loaded_a.get("pid")
    # What: gate on pid a and get and isinstance and int and router a before runtime error; why: persistent_capacity_canary admits runtime error only for this predicate and excludes the opposite state.
    if (
        # What: call loaded_a.get with profile; why: persistent_capacity_canary invokes loaded_a.get while performing or not isinstance router a dict or; the call advances that operation through its result or side effect.
        loaded_a.get("profile") != "model-a" or not isinstance(pid_a, int) or pid_a <= 0
        # What: call isinstance with router a and dict; why: persistent_capacity_canary invokes isinstance while performing or router a get active identity matches engine is not; the call advances that operation through its result or side effect.
        or not isinstance(router_a, dict) or router_a.get("persistent") is not True
        # What: call router_a.get with active identity matches engine; why: persistent_capacity_canary consumes the router_a.get return value while evaluating or router_a.get("activeIdentityMatchesEngine") is not True.
        or router_a.get("activeIdentityMatchesEngine") is not True
    # What: complete the enclosing predicate with if loaded a get profile differs from model a or not isinstance; why: persistent_capacity_canary groups the supplied clauses as one enclosing predicate expression before its value is consumed.
    ):
        # What: raise RuntimeError for the caller; why:  persistent_capacity_canary stops this rejected path before it can mutate state, dispatch work, or report success.
        raise RuntimeError("model-a did not occupy the persistent resident slot")
    # What: compute rejection raw from the named fixture input; why: rejection raw exc read later reads rejection raw, so persistent_capacity_canary must retain the computed value under that name.
    rejection_raw = b""
    # What: establish the handler boundary for the protected operation; why: persistent_capacity_canary routes failures to httperror and error and urllib while preserving cleanup and success flow.
    try:
        # What: map the name field as model b; why: persistent_capacity_canary carries name through request_json(base + "/router/load", {"name": "model-b"}, timeout=30) into raise runtime error persistent capacity conflict returned the.
        request_json(base + "/router/load", {"name": "model-b"}, timeout=30)
    # What: handle httperror and error and urllib by rejection raw exc read 1024 1024 1; why: persistent_capacity_canary converts that failure into this concrete recovery, response, or cleanup behavior.
    except urllib.error.HTTPError as exc:
        # What: compute rejection raw from read and exc and 1 and 1024 and 1024; why: if exc code or len rejection raw later reads rejection raw, so persistent_capacity_canary must retain the computed value under that name.
        rejection_raw = exc.read(1024 * 1024 + 1)
        # What: gate on code and exc and len and rejection raw before exc and runtime error; why: persistent_capacity_canary admits exc and runtime error only for this predicate and excludes the opposite state.
        if exc.code != 409 or len(rejection_raw) > 1024 * 1024:
            # What: raise RuntimeError for the caller; why:  persistent_capacity_canary stops this rejected path before it can mutate state, dispatch work, or report success.
            raise RuntimeError("persistent capacity conflict returned an invalid response") from exc
    # What: select the remaining branch that performs raise runtime error persistent resident allowed a; why: persistent_capacity_canary covers the state excluded by the preceding predicate without conflating the two outcomes.
    else:
        # What: raise RuntimeError for the caller; why:  persistent_capacity_canary stops this rejected path before it can mutate state, dispatch work, or report success.
        raise RuntimeError("persistent resident allowed a conflicting activation")
    # What: establish the handler boundary for the protected operation; why: persistent_capacity_canary routes failures to unicode decode error and jsondecode error and json while preserving cleanup and success flow.
    try:
        # What: compute rejection from loads and rejection raw and json; why: if rejection get error get type capacity unavailable later reads rejection, so persistent_capacity_canary must retain the computed value under that name.
        rejection = json.loads(rejection_raw)
    # What: handle unicode decode error and jsondecode error and json by raise runtime error persistent capacity response was not; why: persistent_capacity_canary converts that failure into this concrete recovery, response, or cleanup behavior.
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        # What: raise RuntimeError for the caller; why:  persistent_capacity_canary stops this rejected path before it can mutate state, dispatch work, or report success.
        raise RuntimeError("persistent capacity response was not JSON") from exc
    # What: gate on get and rejection before runtime error; why: persistent_capacity_canary admits runtime error only for this predicate and excludes the opposite state.
    if rejection.get("error", {}).get("type") != "capacity_unavailable":
        # What: raise RuntimeError for the caller; why:  persistent_capacity_canary stops this rejected path before it can mutate state, dispatch work, or report success.
        raise RuntimeError("persistent capacity conflict returned the wrong error type")
    # What: compute and still a from request json and base and router and status; why: value loaded b request json base router load later reads and still a, so persistent_capacity_canary must retain the computed value under that name.
    _, still_a = request_json(base + "/router/status")
    # What: gate on pid a and get and still a and request json and base before runtime error; why: persistent_capacity_canary admits runtime error only for this predicate and excludes the opposite state.
    if (
        # What: call still_a.get with active profile; why: persistent_capacity_canary invokes still_a.get while performing or still a get active identity matches engine is not; the call advances that operation through its result or side effect.
        still_a.get("activeProfile") != "model-a"
        # What: call still_a.get with active identity matches engine; why: persistent_capacity_canary invokes still_a.get while performing or still a get persistent is not; the call advances that operation through its result or side effect.
        or still_a.get("activeIdentityMatchesEngine") is not True
        # What: call still_a.get with persistent; why: persistent_capacity_canary invokes still_a.get while performing or request json base engine status get; the call advances that operation through its result or side effect.
        or still_a.get("persistent") is not True
        # What: call operation.get with pid; why: persistent_capacity_canary consumes the operation.get return value while evaluating or request_json(base + "/engine/status")[1].get("pid") != pid_a.
        or request_json(base + "/engine/status")[1].get("pid") != pid_a
    # What: complete the enclosing predicate with if still a get active profile differs from model a or still a get active identity matches engine; why: persistent_capacity_canary groups the supplied clauses as one enclosing predicate expression before its value is consumed.
    ):
        # What: raise RuntimeError for the caller; why:  persistent_capacity_canary stops this rejected path before it can mutate state, dispatch work, or report success.
        raise RuntimeError("persistent capacity rejection disturbed the resident engine")
    # What: map the name field as model a; why: persistent_capacity_canary carries name into if request_json(base + "/router/unload", {"name": "model-a"}, timeout=45.
    if request_json(base + "/router/unload", {"name": "model-a"}, timeout=45)[1].get("unloaded") is not True:
        # What: raise RuntimeError for the caller; why:  persistent_capacity_canary stops this rejected path before it can mutate state, dispatch work, or report success.
        raise RuntimeError("explicit persistent unload failed")
    # What: map the name field as model b; why: persistent_capacity_canary carries name through and loaded b into the enclosing return or state update.
    _, loaded_b = request_json(base + "/router/load", {"name": "model-b"}, timeout=660)
    # What: gate on get and loaded b before runtime error; why: persistent_capacity_canary admits runtime error only for this predicate and excludes the opposite state.
    if loaded_b.get("profile") != "model-b" or loaded_b.get("router", {}).get("activeIdentityMatchesEngine") is not True:
        # What: raise RuntimeError for the caller; why:  persistent_capacity_canary stops this rejected path before it can mutate state, dispatch work, or report success.
        raise RuntimeError("released persistent capacity did not admit model-b")
    # What: return rejection raw; why: the caller consumes this value as the function’s success-path result.
    return rejection_raw, {
        # What: map the persistent profile field as model a; why: persistent_capacity_canary carries persistent profile into "persistentProfile": "model-a", "conflictingProfile": "model-b".
        "persistentProfile": "model-a", "conflictingProfile": "model-b",
        # What: map the rejected status field as 409; why: persistent_capacity_canary carries rejected status into "rejectedStatus": 409, "residentPidPreserved": True.
        "rejectedStatus": 409, "residentPidPreserved": True,
        # What: map the explicit unload released capacity field as true; why: persistent_capacity_canary carries explicit unload released capacity into "explicitUnloadReleasedCapacity": True, "passed": True.
        "explicitUnloadReleasedCapacity": True, "passed": True,
    # What: execute the grouped source fragment; why:  the enclosing symbol requires this operation for its concrete qualification or routing path.
    }


# What: define ttl_eviction_canary around base and catalog path and model a and model b and seconds and api key; why: its direct callers call ttl_eviction_canary for ttl eviction canary and rely on this exact input and result contract.
def ttl_eviction_canary(
    # What: declare the base input for ttl_eviction_canary; why: ttl_eviction_canary consumes base during value before request json base router status, so callers must bind it with the other signature inputs.
    base: str, catalog_path: Path, model_a: str, model_b: str, *, seconds: float = 180,
    # What: declare the api key input for ttl_eviction_canary; why: ttl_eviction_canary consumes api key during native catalog text model a model b ttl s api key api key, so callers must bind it with the other signature inputs.
    api_key: str | None = None,
# What: complete the enclosing predicate with dict; why: ttl_eviction_canary groups the supplied clauses as one enclosing predicate expression before its value is consumed.
) -> dict:
    """Exercise idle-TTL ownership cleanup against the temporary catalog only."""
    # What: document exercise idle ttl ownership cleanup against the in the ttl_eviction_canary docstring; why: introspection and maintainers read this exact docstring fragment to understand ttl eviction canary behavior without executing it.
    # What: compute and before from request json and base and router and status; why: value unloaded request json base router unload later reads and before, so ttl_eviction_canary must retain the computed value under that name.
    _, before = request_json(base + "/router/status")
    # What: compute prior evictions from get and before and evictions; why: if not isinstance prior evictions int later reads prior evictions, so ttl_eviction_canary must retain the computed value under that name.
    prior_evictions = before.get("evictions")
    # What: gate on isinstance and prior evictions and int before runtime error; why: ttl_eviction_canary admits runtime error only for this predicate and excludes the opposite state.
    if not isinstance(prior_evictions, int):
        # What: raise RuntimeError for the caller; why:  ttl_eviction_canary stops this rejected path before it can mutate state, dispatch work, or report success.
        raise RuntimeError("router status lacks eviction counter")  # noqa: TRY004 -- malformed remote status is an operational failure.
    # What: compute and unloaded from request json and base and router and unload and 45; why: value reloaded request json base router reload later reads and unloaded, so ttl_eviction_canary must retain the computed value under that name.
    _, unloaded = request_json(base + "/router/unload", {}, timeout=45)
    # What: gate on get and unloaded before runtime error; why: ttl_eviction_canary admits runtime error only for this predicate and excludes the opposite state.
    if unloaded.get("unloaded") is not True:
        # What: raise RuntimeError for the caller; why:  ttl_eviction_canary stops this rejected path before it can mutate state, dispatch work, or report success.
        raise RuntimeError("could not unload the prior resident before TTL qualification")
    # What: extract the router state returned by explicit unload; why: manual unload is itself an eviction and advances the counter before the TTL event under test.
    unloaded_router = unloaded.get("router")
    # What: validate and retain the post-unload eviction baseline; why: the TTL assertion must measure one additional automatic eviction rather than compare against stale pre-unload accounting.
    if not isinstance(unloaded_router, dict) or unloaded_router.get("evictions") != prior_evictions + 1:
        # What: reject inconsistent explicit-unload accounting; why: a missing baseline would let the later TTL counter produce ambiguous evidence.
        raise RuntimeError("explicit unload did not advance eviction accounting exactly once")
    # What: retain the exact post-unload counter; why: the automatic TTL event must increment this current baseline by one.
    unloaded_evictions = unloaded_router["evictions"]
    # What: call catalog_path.write_text with native catalog text and model a and model b and api key and 2; why: ttl_eviction_canary invokes catalog_path.write_text while performing native catalog text model a model b ttl s api key api key; the call advances that operation through its result or side effect.
    catalog_path.write_text(
        # What: preserve the exact native catalog text model a model b ttl s api key api key literal fragment; why: ttl_eviction_canary passes this fragment verbatim through native_catalog_text(model_a, model_b, ttl_s=2, api_key=api_key), encodin, because changing it would alter a protocol payload, serialized fixture.
        native_catalog_text(model_a, model_b, ttl_s=2, api_key=api_key), encoding="utf-8"
    # What: complete the catalog_path.write_text call with encoding; why: ttl_eviction_canary groups the supplied clauses as one catalog_path.write_text call before its value is consumed.
    )
    # What: compute and reloaded from request json and base and router and reload and 30; why: value loaded request json base router load later reads and reloaded, so ttl_eviction_canary must retain the computed value under that name.
    _, reloaded = request_json(base + "/router/reload", {}, timeout=30)
    # What: gate on get and reloaded before runtime error; why: ttl_eviction_canary admits runtime error only for this predicate and excludes the opposite state.
    if reloaded.get("reloaded") is not True:
        # What: raise RuntimeError for the caller; why:  ttl_eviction_canary stops this rejected path before it can mutate state, dispatch work, or report success.
        raise RuntimeError("temporary TTL catalog reload was not acknowledged")
    # What: map the name field as model a; why: ttl_eviction_canary carries name through and loaded into the enclosing return or state update.
    _, loaded = request_json(base + "/router/load", {"name": "model-a"}, timeout=660)
    # What: compute port from get and loaded and port; why: if loaded get profile model a or not later reads port, so ttl_eviction_canary must retain the computed value under that name.
    port = loaded.get("port")
    # What: gate on get and isinstance and port and int and loaded before runtime error; why: ttl_eviction_canary admits runtime error only for this predicate and excludes the opposite state.
    if loaded.get("profile") != "model-a" or not isinstance(port, int) or not 1 <= port <= 65535:
        # What: raise RuntimeError for the caller; why:  ttl_eviction_canary stops this rejected path before it can mutate state, dispatch work, or report success.
        raise RuntimeError("TTL qualification did not activate a concrete model-a engine")
    # What: complete one routed request against the TTL-enabled resident; why: idle eviction is scheduled when request ownership is released, not merely when an operator preloads a model.
    _, ttl_completion = canary(base, "model-a", direct=False)
    # What: reject a failed TTL trigger completion; why: eviction evidence is only meaningful after the resident has served and released real inference work.
    if ttl_completion.get("passed") is not True:
        # What: stop the TTL gate when the trigger request fails; why: waiting for eviction without proven prior use would test the wrong lifecycle contract.
        raise RuntimeError("TTL qualification trigger completion failed")
    # What: compute deadline from seconds and monotonic and time; why: while time monotonic deadline later reads deadline, so ttl_eviction_canary must retain the computed value under that name.
    deadline = time.monotonic() + seconds
    # What: compute status from the named fixture input; why: status request json base router status timeout later reads status, so ttl_eviction_canary must retain the computed value under that name.
    status: dict | None = None
    # What: iterate across deadline and monotonic and time to perform status and request json and base; why: ttl_eviction_canary repeats the body only while or for the loop header admits an iteration.
    while time.monotonic() < deadline:
        # What: compute status from request json and base and 1 and router and status; why: if status get active profile is and status get later reads status, so ttl_eviction_canary must retain the computed value under that name.
        status = request_json(base + "/router/status", timeout=3)[1]
        # What: gate on get and prior evictions and status before the computed value; why: ttl_eviction_canary admits the computed value only for this predicate and excludes the opposite state.
        if status.get("activeProfile") is None and status.get("evictions") == unloaded_evictions + 1:
            # What: apply the break portion of the enclosing predicate; why: this clause remains in ttl_eviction_canary\'s enclosing expression so its grouping and evaluation order stay intact.
            break
        # What: call time.sleep with 0 1; why: ttl_eviction_canary invokes time.sleep while performing if status is or status get active profile; the call advances that operation through its result or side effect.
        time.sleep(0.1)
    # What: gate on status and get and prior evictions before timeout error; why: ttl_eviction_canary admits timeout error only for this predicate and excludes the opposite state.
    if status is None or status.get("activeProfile") is not None or status.get("evictions") != unloaded_evictions + 1:
        # What: raise TimeoutError for the caller; why: ttl_eviction_canary stops this rejected path before it can mutate state, dispatch work, or report success.
        raise TimeoutError("idle TTL did not evict the temporary resident engine")
    # What: call require_listener_closed with port; why: ttl_eviction_canary invokes require_listener_closed while performing return; the call advances that operation through its result or side effect.
    require_listener_closed(port)
    # What: return port and profile and ttl seconds and port and eviction incremented from ttl_eviction_canary; why: ttl_eviction_canary exposes port and profile and ttl seconds and port and eviction incremented so its caller can continue with the function\'s computed outcome.
    return {
        # What: map the profile field as model a; why: ttl_eviction_canary carries profile into "profile": "model-a".
        "profile": "model-a",
        # What: map the ttl seconds field as 2; why: ttl_eviction_canary carries ttl seconds into "ttlSeconds": 2.
        "ttlSeconds": 2,
        # What: map the port field as port; why: ttl_eviction_canary carries port into "port": port.
        "port": port,
        # What: map the eviction incremented field as true; why: ttl_eviction_canary carries eviction incremented into "evictionIncremented": True.
        "evictionIncremented": True,
        # What: map the listener closed field as true; why: ttl_eviction_canary carries listener closed into "listenerClosed": True.
        "listenerClosed": True,
        # What: map the passed field as true; why: ttl_eviction_canary carries passed into "passed": True.
        "passed": True,
    # What: complete the enclosing predicate mapping with profile and ttl seconds and port and eviction incremented and listener closed; why: ttl_eviction_canary groups the supplied clauses as one enclosing predicate mapping mapping before its value is consumed.
    }


# What: define native_catalog_text around model a and model b and ttl s and model a priority and invalid model and persistent a and api key and startup; why: its direct callers call native_catalog_text for native catalog text and rely on this exact input and result contract.
def native_catalog_text(
    # What: declare the model a input for native_catalog_text; why: native_catalog_text consumes model a during for alias model in model a model a, so callers must bind it with the other signature inputs.
    model_a: str, model_b: str, *, ttl_s: int = 0, model_a_priority: int = 0,
    # What: declare the invalid model input for native_catalog_text; why: native_catalog_text consumes invalid model during if invalid model is not, so callers must bind it with the other signature inputs.
    invalid_model: str | None = None, persistent_a: bool = False,
    # What: declare the api key input for native_catalog_text; why: native_catalog_text consumes api key during if api key is not, so callers must bind it with the other signature inputs.
    api_key: str | None = None, startup: bool = False,
# What: complete the enclosing predicate with str; why: native_catalog_text groups the supplied clauses as one enclosing predicate expression before its value is consumed.
) -> str:
    """Return the allowlisted, dynamic-port catalog used by the private run."""
    # What: document return the allowlisted dynamic port catalog used in the native_catalog_text docstring; why: introspection and maintainers read this exact docstring fragment to understand native catalog text behavior without executing it.
    # What: compute common args from host and 127 0 0 1 and served model name and model id and max seq len override; why: args json dumps common args replace model id alias later reads common args, so native_catalog_text must retain the computed value under that name.
    common_args = [
        # What: apply the host served model name model id portion of common args; why: native_catalog_text uses this clause to evaluate common args as one grouped value.
        "--host", "127.0.0.1", "--served-model-name", "${MODEL_ID}",
        # What: bound sequence, cache, and prefill capacity for the 24 GiB gfx1150 host; why: both qualified checkpoints need deterministic headroom instead of an avoidable recurrent-state allocation failure.
        "--max-seq-len-override", "1024", "--num-tokens", "1024", "--max-prefill-length", "256",
        # What: use one captured request, the naive cache, and a measured memory ratio; why: LAN-215 must avoid unsupported hybrid-state over-allocation while preserving enough memory for both exact artifacts.
        "--max-running-requests", "1", "--graph", "1", "--cache-type", "naive", "--memory-ratio", "0.90",
        # What: apply the attention backend triton moe backend fused disable pynccl portion of common args; why: native_catalog_text uses this clause to evaluate common args as one grouped value.
        "--attention-backend", "triton", "--moe-backend", "fused", "--disable-pynccl",
    # What: complete the common_args collection with host and 127 0 0 1 and served model name and model id; why: native_catalog_text groups the supplied clauses as one common_args collection before its value is consumed.
    ]
    # What: compute catalog from router and upstream timeout s and include aliases in list and true and send loading state; why: catalog f api keys json dumps api key later reads catalog, so native_catalog_text must retain the computed value under that name.
    catalog = [
        # What: apply the router upstream timeout s include aliases in list true portion of catalog; why: native_catalog_text uses this clause to evaluate catalog as one grouped value.
        "[router]", "upstream_timeout_s = 660", "include_aliases_in_list = true",
        # What: apply the send loading state true performance every s portion of catalog; why: native_catalog_text uses this clause to evaluate catalog as one grouped value.
        "send_loading_state = true", "performance_every_s = 5", "",
    # What: complete the catalog collection with router and upstream timeout s and include aliases in list and true and send loading state and true; why: native_catalog_text groups the supplied clauses as one catalog collection before its value is consumed.
    ]
    # What: gate on api key before catalog and dumps and api key and json; why: native_catalog_text admits catalog and dumps and api key and json only for this predicate and excludes the opposite state.
    if api_key is not None:
        # What: compute catalog entry from dumps and api key and json and api keys and value; why: catalog later reads catalog entry, so native_catalog_text must retain the computed value under that name.
        catalog[2:2] = [f"api_keys = [{json.dumps(api_key)}]"]
    # What: gate on startup before catalog; why: native_catalog_text admits catalog only for this predicate and excludes the opposite state.
    if startup:
        # What: compute catalog entry from preload model and compat and model a and startup routing profile and coding; why: catalog extend later reads catalog entry, so native_catalog_text must retain the computed value under that name.
        catalog[-1:-1] = [
            # What: apply the preload model compat model a portion of catalog entry; why: native_catalog_text uses this clause to evaluate catalog entry as one grouped value.
            'preload_model = "compat/model-a"',
            # What: apply the startup routing profile coding portion of catalog entry; why: native_catalog_text uses this clause to evaluate catalog entry as one grouped value.
            'startup_routing_profile = "coding"',
        # What: complete the catalog entry collection with preload model and compat and model a and startup routing profile and coding; why: native_catalog_text groups the supplied clauses as one catalog entry collection before its value is consumed.
        ]
    # What: call catalog.extend with selectors and preferred model and strategy and warm and targets; why: native_catalog_text invokes catalog.extend while performing selectors preferred model strategy warm; the call advances that operation through its result or side effect.
    catalog.extend((
        # What: preserve the exact selectors preferred model strategy warm literal fragment; why: native_catalog_text passes this fragment verbatim through "[selectors.preferred-model]", 'strategy = "warm"', because changing it would alter a protocol payload, serialized fixture, or public message.
        "[selectors.preferred-model]", 'strategy = "warm"',
        # What: preserve the exact targets model b model a name preferred local literal fragment; why: native_catalog_text passes this fragment verbatim through 'targets = ["model-b", "model-a"]', 'name = "Preferred local model"', because changing it would alter a protocol payload, serialized fixture, or public messag.
        'targets = ["model-b", "model-a"]', 'name = "Preferred local model"',
        # What: preserve the exact description reuses a ready target before literal fragment; why: native_catalog_text passes this fragment verbatim through 'description = "Reuses a ready target before the ordered cold fallback"', because changing it would alter a protocol payload, serialized fixture, or public messag.
        'description = "Reuses a ready target before the ordered cold fallback"', "",
        # What: preserve the exact profiles coding description qualification routing profile literal fragment; why: native_catalog_text passes this fragment verbatim through "[profiles.coding]", 'description = "Qualification routing profile"', because changing it would alter a protocol payload, serialized fixture, or.
        "[profiles.coding]", 'description = "Qualification routing profile"',
        # What: preserve the exact profiles coding pins profile model preferred model literal fragment; why: native_catalog_text passes this fragment verbatim through "[profiles.coding.pins]", 'profile-model = "preferred-model"', because changing it would alter a protocol payload, serialized fixture, or public message.
        "[profiles.coding.pins]", 'profile-model = "preferred-model"',
        # What: preserve the exact disabled model literal fragment; why: native_catalog_text passes this fragment verbatim through 'disabled-model = ""', "", because changing it would alter a protocol payload, serialized fixture, or public message.
        'disabled-model = ""', "",
    # What: complete the catalog.extend call with ordered positional inputs; why: native_catalog_text groups the supplied clauses as one catalog.extend call before its value is consumed.
    ))
    # What: gate on persistent a before extend and catalog; why: native_catalog_text admits extend and catalog only for this predicate and excludes the opposite state.
    if persistent_a:
        # What: call catalog.extend with router and groups and resident and members and model a; why: native_catalog_text invokes catalog.extend while performing router groups resident members model a swap false; the call advances that operation through its result or side effect.
        catalog.extend((
            # What: preserve the exact router groups resident members model a swap false literal fragment; why: native_catalog_text passes this fragment verbatim through "[router.groups.resident]", 'members = ["model-a"]', "swap = false", because changing it would alter a protocol payload, serialized fixture, or publi.
            "[router.groups.resident]", 'members = ["model-a"]', "swap = false",
            # What: preserve the exact exclusive true persistent true literal fragment; why: native_catalog_text passes this fragment verbatim through "exclusive = true", "persistent = true", "", because changing it would alter a protocol payload, serialized fixture, or public message.
            "exclusive = true", "persistent = true", "",
        # What: complete the catalog.extend call with ordered positional inputs; why: native_catalog_text groups the supplied clauses as one catalog.extend call before its value is consumed.
        ))
    # What: iterate across model a and model b to perform profile lines and alias and ttl s and dumps and model; why: native_catalog_text repeats the body only while or for the loop header admits an iteration.
    for alias, model in (("model-a", model_a), ("model-b", model_b)):
        # What: compute profile lines from alias and ttl s and dumps and model; why: profile lines append group resident later reads profile lines, so native_catalog_text must retain the computed value under that name.
        profile_lines = [
            # What: call json.dumps with model; why: native_catalog_text invokes json.dumps while performing check endpoint ready proxy http port; the call advances that operation through its result or side effect.
            f"[models.{alias}]", f"model = {json.dumps(model)}", "port = 0", "ready_timeout_s = 600",
            # What: apply the check endpoint ready proxy http port portion of profile lines; why: native_catalog_text uses this clause to evaluate profile lines as one grouped value.
            'check_endpoint = "/ready"', 'proxy = "http://127.0.0.1:${PORT}"',
            # What: call json.dumps with alias; why: native_catalog_text invokes json.dumps while performing upstream timeout s; the call advances that operation through its result or side effect.
            f"use_model_name = {json.dumps(alias)}",
            # What: apply the upstream timeout s portion of profile lines; why: native_catalog_text uses this clause to evaluate profile lines as one grouped value.
            "upstream_timeout_s = 659",
            # What: apply the f ttl s ttl s f priority model a priority portion of profile lines; why: native_catalog_text uses this clause to evaluate profile lines as one grouped value.
            f"ttl_s = {ttl_s}", f"priority = {model_a_priority if alias == 'model-a' else 0}",
        # What: complete the profile_lines collection with alias and models and value and dumps and model and json and model and port and ready timeout s; why: native_catalog_text groups the supplied clauses as one profile_lines collection before its value is consumed.
        ]
        # What: gate on persistent a and alias before append and profile lines; why: native_catalog_text admits append and profile lines only for this predicate and excludes the opposite state.
        if persistent_a and alias == "model-a":
            # What: preserve the exact profile lines append group resident literal fragment; why: native_catalog_text passes this fragment verbatim through profile_lines.append('group = "resident"'), because changing it would alter a protocol payload, serialized fixture, or public message.
            profile_lines.append('group = "resident"')
        # What: gate on alias before append and profile lines; why: native_catalog_text admits append and profile lines only for this predicate and excludes the opposite state.
        if alias == "model-a":
            # What: preserve the exact profile lines append name qualification model a literal fragment; why: native_catalog_text passes this fragment verbatim through profile_lines.append('name = "Qualification model A"'), because changing it would alter a protocol payload, serialized fixture, or public message.
            profile_lines.append('name = "Qualification model A"')
            # What: preserve the exact profile lines append aliases compat model a literal fragment; why: native_catalog_text passes this fragment verbatim through profile_lines.append('aliases = ["compat/model-a"]'), because changing it would alter a protocol payload, serialized fixture, or public message.
            profile_lines.append('aliases = ["compat/model-a"]')
        # What: call profile_lines.extend with replace and alias and dumps and common args; why: native_catalog_text invokes profile_lines.extend while performing args json dumps common args replace model id alias; the call advances that operation through its result or side effect.
        profile_lines.extend((
            # What: preserve the exact args json dumps common args replace model id alias literal fragment; why: native_catalog_text passes this fragment verbatim through "args = " + json.dumps(common_args).replace("${MODEL_ID}", alias), "", because changing it would alter a protocol payload, serialized fixture, or pu.
            "args = " + json.dumps(common_args).replace("${MODEL_ID}", alias), ""
        # What: complete the profile_lines.extend call with replace; why: native_catalog_text groups the supplied clauses as one profile_lines.extend call before its value is consumed.
        ))
        # What: gate on alias before extend and profile lines; why: native_catalog_text admits extend and profile lines only for this predicate and excludes the opposite state.
        if alias == "model-a":
            # What: call profile_lines.extend with models and model a and metadata and tier and qualification; why: native_catalog_text invokes profile_lines.extend while performing models model a metadata tier qualification; the call advances that operation through its result or side effect.
            profile_lines.extend((
                # What: preserve the exact models model a metadata tier qualification literal fragment; why: native_catalog_text passes this fragment verbatim through "[models.model-a.metadata]", 'tier = "qualification"', because changing it would alter a protocol payload, serialized fixture, or public message.
                "[models.model-a.metadata]", 'tier = "qualification"',
                # What: preserve the exact type operator literal fragment; why: native_catalog_text passes this fragment verbatim through 'type = "operator"', "", because changing it would alter a protocol payload, serialized fixture, or public message.
                'type = "operator"', "",
            # What: complete the profile_lines.extend call with ordered positional inputs; why: native_catalog_text groups the supplied clauses as one profile_lines.extend call before its value is consumed.
            ))
        # What: call catalog.extend with profile lines; why: native_catalog_text invokes catalog.extend while performing if invalid model is not; the call advances that operation through its result or side effect.
        catalog.extend(profile_lines)
    # What: gate on invalid model before extend and catalog and replace and dumps and invalid model; why: native_catalog_text admits extend and catalog and replace and dumps and invalid model only for this predicate and excludes the opposite state.
    if invalid_model is not None:
        # What: call catalog.extend with replace and dumps and invalid model and json; why: native_catalog_text invokes catalog.extend while performing models model invalid f model json dumps invalid model port; the call advances that operation through its result or side effect.
        catalog.extend((
            # What: preserve the exact models model invalid f model json dumps invalid model port literal fragment; why: native_catalog_text passes this fragment verbatim through "[models.model-invalid]", f"model = {json.dumps(invalid_model)}", "port, because changing it would alter a protocol payload, serialized fixt.
            "[models.model-invalid]", f"model = {json.dumps(invalid_model)}", "port = 0",
            # What: preserve the exact ready timeout s check endpoint ready literal fragment; why: native_catalog_text passes this fragment verbatim through "ready_timeout_s = 15", 'check_endpoint = "/ready"', because changing it would alter a protocol payload, serialized fixture, or public message.
            "ready_timeout_s = 15", 'check_endpoint = "/ready"',
            # What: preserve the exact proxy http port ttl s literal fragment; why: native_catalog_text passes this fragment verbatim through 'proxy = "http://127.0.0.1:${PORT}"', "ttl_s = 0", because changing it would alter a protocol payload, serialized fixture, or public message.
            'proxy = "http://127.0.0.1:${PORT}"', "ttl_s = 0",
            # What: preserve the exact args json dumps common args replace model id model invalid literal fragment; why: native_catalog_text passes this fragment verbatim through "args = " + json.dumps(common_args).replace("${MODEL_ID}", "model-invali, because changing it would alter a protocol payload, serialized fix.
            "args = " + json.dumps(common_args).replace("${MODEL_ID}", "model-invalid"), "",
        # What: complete the catalog.extend call with replace; why: native_catalog_text groups the supplied clauses as one catalog.extend call before its value is consumed.
        ))
    # What: return join and catalog and value from native_catalog_text; why: native_catalog_text exposes join and catalog and value so its caller can continue with the function\'s computed outcome.
    return "\n".join(catalog)


# What: define main around the current object state; why: its direct callers call main for main and rely on this exact input and result contract.
def main() -> int:
    # What: compute parser from argument parser and argparse and doc; why: parser add argument name required later reads parser, so main must retain the computed value under that name.
    parser = argparse.ArgumentParser(description=__doc__)
    # What: iterate across the computed value to perform add argument and parser and name; why: main repeats the body only while or for the loop header admits an iteration.
    for name in (
        # What: apply the source python model a model b artifacts protected service portion of the enclosing predicate; why: this clause remains in main\'s enclosing expression so its grouping and evaluation order stay intact.
        "source", "python", "model-a", "model-b", "artifacts", "protected-service", "protected-url",
        # What: apply the expected hostname portion of the enclosing predicate; why: this clause remains in main\'s enclosing expression so its grouping and evaluation order stay intact.
        "expected-hostname",
    # What: complete the enclosing predicate collection with source and python and model a and model b; why: main groups the supplied clauses as one enclosing predicate collection collection before its value is consumed.
    ):
        # What: register the parser add argument name required True command-line option; why: main validates this operator input before starting the qualification sequence.
        parser.add_argument("--" + name, required=True)
    # What: register the parser add argument allow maintenance action store true required True command-line option; why: main validates this operator input before starting the qualification sequence.
    parser.add_argument("--allow-maintenance", action="store_true", required=True)
    # What: preserve the exact parser add argument daemon port type int default literal fragment; why: main passes this fragment verbatim through parser.add_argument("--daemon-port", type=int, default=1964), because changing it would alter a protocol payload, serialized fixture, or public message.
    # What: register protected-service ownership scope; why: the harness must stop and restore the exact manager that owns the workload.
    parser.add_argument("--protected-service-scope", choices=("system", "user"), default="system")
    # What: register an optional watchdog maintenance marker path; why: a protected-service timer must not race the harness by restarting the workload during an owned GPU window.
    parser.add_argument("--protected-maintenance-marker")
    # What: preserve the temporary daemon port option; why: callers still need a collision-free loopback control-plane endpoint.
    parser.add_argument("--daemon-port", type=int, default=1964)
    # What: compute args from parse args and parser; why: require expected hostname args expected hostname later reads args, so main must retain the computed value under that name.
    args = parser.parse_args()
    # What: gate on startswith and platform and sys before system exit; why: main admits system exit only for this predicate and excludes the opposite state.
    if not sys.platform.startswith("linux"):
        # What: raise SystemExit for the caller; why: main stops this rejected path before it can mutate state, dispatch work, or report success.
        raise SystemExit("native maintenance qualification requires Linux process-group semantics")
    # What: call require_expected_hostname with expected hostname and args; why: main invokes require_expected_hostname while performing artifacts path args artifacts; the call advances that operation through its result or side effect.
    require_expected_hostname(args.expected_hostname)

    # What: compute artifacts from path and artifacts and args; why: artifacts mkdir parents exist ok later reads artifacts, so main must retain the computed value under that name.
    artifacts = Path(args.artifacts)
    # What: supply parents to artifacts.mkdir; why: main binds this true value to artifacts.mkdir's parents input.
    artifacts.mkdir(parents=True, exist_ok=False)
    # What: map the trials field as the fixture input; why: main carries trials through result into artifacts result json write text json dumps result indent 2.
    result: dict = {"trials": [], "restored": False}

    # What: define save around the current object state; why: its direct callers call save for save and rely on this exact input and result contract.
    def save() -> None:
        # What: preserve the exact artifacts result json write text json dumps result indent literal fragment; why: save passes this fragment verbatim through (artifacts / "result.json").write_text(json.dumps(result, indent=2), enc, because changing it would alter a protocol payload, serialized fixture, or public mess.
        (artifacts / "result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")

    # What: compute service from sudo and n and systemctl; why: subprocess run service is active quiet args protected service check later reads service, so main must retain the computed value under that name.
    # What: select the exact protected-service manager; why: maintenance and restoration must use the unit's real ownership scope.
    service = protected_service_command(args.protected_service_scope)
    # What: execute subprocess run service is active quiet args protected service check True; why: the enclosing symbol requires this operation for its concrete qualification or routing path.
    subprocess.run(service + ["is-active", "--quiet", args.protected_service], check=True)
    # What: compute baseline raw and baseline from request json and protected url and args and health and 10; why: artifacts protected baseline health json write bytes baseline raw later reads baseline raw and baseline, so main must retain the computed value under that name.
    baseline_raw, baseline = request_json(args.protected_url + "/health", timeout=10)
    # What: preserve the exact artifacts protected baseline health json write bytes baseline raw literal fragment; why: main passes this fragment verbatim through (artifacts / "protected-baseline-health.json").write_bytes(baseline_raw), because changing it would alter a protocol payload, serialized fixture, or public.
    (artifacts / "protected-baseline-health.json").write_bytes(baseline_raw)
    # What: gate on get and baseline before runtime error; why: main admits runtime error only for this predicate and excludes the opposite state.
    if baseline.get("status") != "ok":
        # What: raise RuntimeError for the caller; why:  main stops this rejected path before it can mutate state, dispatch work, or report success.
        raise RuntimeError("protected service health baseline failed; no maintenance performed")
    # What: compute and listing from request json and protected url and args and v1 and models; why: protected raw value canary args protected url protected model direct later reads and listing, so main must retain the computed value under that name.
    _, listing = request_json(args.protected_url + "/v1/models", timeout=10)
    # What: compute protected model from listing and id and 0 and data; why: protected raw value canary args protected url protected model direct later reads protected model, so main must retain the computed value under that name.
    protected_model = listing["data"][0]["id"]
    # What: compute protected raw and from canary and protected url and protected model and args and true; why: artifacts protected baseline response sse write bytes protected raw later reads protected raw and, so main must retain the computed value under that name.
    protected_raw, _ = canary(args.protected_url, protected_model, direct=True)
    # What: preserve the exact artifacts protected baseline response sse write bytes protected raw literal fragment; why: main passes this fragment verbatim through (artifacts / "protected-baseline-response.sse").write_bytes(protected_ra, because changing it would alter a protocol payload, serialized fixture, or publi.
    (artifacts / "protected-baseline-response.sse").write_bytes(protected_raw)

    # What: compute env from copy and environ and os; why: env pythonpath str path args source python later reads env, so main must retain the computed value under that name.
    env = os.environ.copy()
    # What: compute env entry from str and path and source and args and python; why: env torch extensions dir str artifacts torch extensions later reads env entry, so main must retain the computed value under that name.
    env["PYTHONPATH"] = str(Path(args.source) / "python")
    # What: compute env entry from str and artifacts and torch extensions; why: env max jobs later reads env entry, so main must retain the computed value under that name.
    env["TORCH_EXTENSIONS_DIR"] = str(artifacts / "torch-extensions")
    # What: compute env entry from 2; why: cwd args source env env stdout log later reads env entry, so main must retain the computed value under that name.
    env["MAX_JOBS"] = "2"
    # What: compute catalog path from artifacts and models and toml; why: catalog path write text later reads catalog path, so main must retain the computed value under that name.
    catalog_path = artifacts / "models.toml"
    # What: compute invalid model from str and artifacts and intentionally missing model and gguf; why: args model a args model b invalid model invalid model api key native api key later reads invalid model, so main must retain the computed value under that name.
    invalid_model = str(artifacts / "intentionally-missing-model.gguf")
    # What: compute native api key from token urlsafe and secrets and 32; why: args model a args model b invalid model invalid model api key native api key later reads native api key, so main must retain the computed value under that name.
    native_api_key = secrets.token_urlsafe(32)
    # What: call catalog_path.write_text with native catalog text and model a and model b and args; why: main invokes catalog_path.write_text while performing native catalog text; the call advances that operation through its result or side effect.
    catalog_path.write_text(
        # What: call native_catalog_text with model a and args and model b and args; why: main invokes native_catalog_text while performing args model a args model b invalid model invalid model api key native api key; the call advances that operation through its result or side effect.
        native_catalog_text(
            # What: supply invalid model to native_catalog_text; why:  main binds this invalid model value to native_catalog_text's invalid model input.
            args.model_a, args.model_b, invalid_model=invalid_model, api_key=native_api_key
        # What: complete the native_catalog_text call with invalid model and api key; why: main groups the supplied clauses as one native_catalog_text call before its value is consumed.
        ),
        # What: preserve the exact encoding utf 8 literal fragment; why: main passes this fragment verbatim through encoding="utf-8", because changing it would alter a protocol payload, serialized fixture, or public message.
        encoding="utf-8",
    # What: complete the catalog_path.write_text call with encoding; why: main groups the supplied clauses as one catalog_path.write_text call before its value is consumed.
    )
    # What: enter the operation.open managed context before subprocess run; why: main releases this resource or lock after subprocess run on both success and failure paths.
    with (artifacts / "kernel-preflight.log").open("wb") as log:
        # What: call subprocess.run with python and args and c and from and freetoken; why: main invokes subprocess.run while performing args python c from freetoken kernel gguf import module; the call advances that operation through its result or side effect.
        subprocess.run(
            # What: preserve the exact args python c from freetoken kernel gguf import module literal fragment; why: main passes this fragment verbatim through [args.python, "-c", "from freetoken.kernel.gguf import _module.
            [args.python, "-c", "from freetoken.kernel.gguf import _module; _module(); print('NATIVE_KERNEL_READY')"],
            # What: supply cwd to subprocess.run; why: main binds this source and args value to subprocess.run's cwd input.
            cwd=args.source, env=env, stdout=log, stderr=subprocess.STDOUT, check=True, timeout=600,
        # What: complete the subprocess.run call with cwd and env and stdout and stderr and check; why: main groups the supplied clauses as one subprocess.run call before its value is consumed.
        )

    # What: compute daemon from the named fixture input; why: args python m freetoken cli daemon host later reads daemon, so main must retain the computed value under that name.
    daemon: subprocess.Popen[bytes] | None = None
    # What: compute detached engine from the named fixture input; why: detached engine old pid old port later reads detached engine, so main must retain the computed value under that name.
    detached_engine: tuple[int, int] | None = None
    # What: compute maintenance from false; why: maintenance later reads maintenance, so main must retain the computed value under that name.
    maintenance = False
    # What: resolve the optional watchdog marker path; why: lifecycle cleanup must track the exact marker that this harness may own.
    maintenance_marker = Path(args.protected_maintenance_marker) if args.protected_maintenance_marker else None
    # What: initialize marker ownership as false; why: cleanup must never remove a marker that predated this qualification run.
    maintenance_marker_owned = False
    # What: compute final engine port from the named fixture input; why: final engine port direct row hardware engine port later reads final engine port, so main must retain the computed value under that name.
    final_engine_port: int | None = None
    # What: compute base from daemon port and args and http; why: configure native auth base native api key later reads base, so main must retain the computed value under that name.
    base = f"http://127.0.0.1:{args.daemon_port}"
    # What: call configure_native_auth with base and native api key; why: main invokes configure_native_auth while performing def launch daemon log stop serve on exit bool subprocess popen; the call advances that operation through its result or side effect.
    configure_native_auth(base, native_api_key)

    # What: define launch_daemon around log and stop serve on exit; why: its direct callers call launch_daemon for launch daemon and rely on this exact input and result contract.
    def launch_daemon(log, *, stop_serve_on_exit: bool) -> subprocess.Popen[bytes]:
        # What: compute command from python and args and str and daemon port; why: command append stop serve on exit later reads command, so launch_daemon must retain the computed value under that name.
        command = [
            # What: apply the args python m freetoken cli daemon host portion of command; why: launch_daemon uses this clause to evaluate command as one grouped value.
            args.python, "-m", "freetoken.cli", "daemon", "--host", "127.0.0.1",
            # What: call str with daemon port and args; why: launch_daemon invokes str while performing catalog str catalog path catalog watch interval no oom; the call advances that operation through its result or side effect.
            "--port", str(args.daemon_port), "--state-dir", str(artifacts / "daemon-state"),
            # What: call str with catalog path; why: launch_daemon consumes the str return value while evaluating "--catalog", str(catalog_path), "--catalog-watch-interval", "0", "--no-o.
            "--catalog", str(catalog_path), "--catalog-watch-interval", "0", "--no-oom",
        # What: complete the command collection with python and args and m and freetoken and cli and daemon; why: launch_daemon groups the supplied clauses as one command collection before its value is consumed.
        ]
        # What: gate on stop serve on exit before append and command; why: launch_daemon admits append and command only for this predicate and excludes the opposite state.
        if stop_serve_on_exit:
            # What: preserve the exact command append stop serve on exit literal fragment; why: launch_daemon passes this fragment verbatim through command.append("--stop-serve-on-exit"), because changing it would alter a protocol payload, serialized fixture, or public message.
            command.append("--stop-serve-on-exit")
        # What: return popen and command and subprocess and source from launch_daemon; why: launch_daemon exposes popen and command and subprocess and source so its caller can continue with the function\'s computed outcome.
        return subprocess.Popen(
            # What: supply cwd to subprocess.Popen; why: launch_daemon binds this source and args value to subprocess.Popen's cwd input.
            command, cwd=args.source, env=env, stdout=log, stderr=subprocess.STDOUT,
            # What: supply stdin to subprocess.Popen; why: launch_daemon binds this devnull and subprocess value to subprocess.Popen's stdin input.
            stdin=subprocess.DEVNULL, start_new_session=True,
        # What: complete the subprocess.Popen call with cwd and env and stdout and stderr and stdin; why: launch_daemon groups the supplied clauses as one subprocess.Popen call before its value is consumed.
        )

    # What: establish the handler boundary for the protected operation; why: main routes failures to base exception while preserving cleanup and success flow.
    try:
        # What: enter the operation.open managed context before daemon launch daemon log stop serve on exit; why: main releases this resource or lock after daemon launch daemon log stop serve on exit on both success and failure paths.
        with (artifacts / "daemon.log").open("wb") as log:
            # What: compute daemon from launch daemon and log and false; why: stop process group daemon later reads daemon, so main must retain the computed value under that name.
            daemon = launch_daemon(log, stop_serve_on_exit=False)
            # What: preserve the exact wait json base router status seconds literal fragment; why: main passes this fragment verbatim through wait_json(base + "/router/status", seconds=30), because changing it would alter a protocol payload, serialized fixture, or public message.
            wait_json(base + "/router/status", seconds=30)
            # What: compute maintenance from true; why: if maintenance later reads maintenance, so main must retain the computed value under that name.
            maintenance = True
            # What: gate marker creation on an explicitly configured path; why: hosts without a watchdog marker preserve their existing lifecycle behavior.
            if maintenance_marker is not None:
                # What: fail if the marker already exists; why: another operator or process may own maintenance and must not be overridden.
                if maintenance_marker.exists():
                    # What: raise a lifecycle ownership error before stopping the service; why: qualification must fail closed when exclusive maintenance cannot be proven.
                    raise RuntimeError("protected-service maintenance marker already exists")
                # What: create the marker with private run context; why: LAN-215's health watchdog must suppress automatic restarts for this exact maintenance window.
                maintenance_marker.write_text("FreeToken native-router qualification owns this maintenance window.\n", encoding="utf-8")
                # What: record marker ownership after successful creation; why: only an owned marker may be removed during restoration.
                maintenance_marker_owned = True
            # What: execute subprocess run service stop args protected service check True timeout 90; why: the enclosing symbol requires this operation for its concrete qualification or routing path.
            subprocess.run(service + ["stop", args.protected_service], check=True, timeout=90)

            # Direct is intentionally measured against the native engine port after a router-owned load.
            # What: map the name field as model a; why: main carries name through loaded raw and loaded into artifacts direct a load json write bytes loaded raw.
            loaded_raw, loaded = request_json(base + "/router/load", {"name": "model-a"}, timeout=660)
            # What: gate on get and isinstance and int and loaded before runtime error; why: main admits runtime error only for this predicate and excludes the opposite state.
            if loaded.get("profile") != "model-a" or not isinstance(loaded.get("port"), int):
                # What: raise RuntimeError for the caller; why:  main stops this rejected path before it can mutate state, dispatch work, or report success.
                raise RuntimeError("native management load did not return a concrete model-a target")
            # What: wait for the router-owned engine's authoritative readiness endpoint; why: a successful lifecycle admission may precede model initialization and must not be mistaken for an inference-ready resident.
            wait_json(f"http://127.0.0.1:{loaded['port']}/ready", seconds=600)
            # What: compute activation count from validate routed trial and loaded and router and model a and 0; why: activation count validate routed trial later reads activation count, so main must retain the computed value under that name.
            activation_count = validate_routed_trial(
                # What: supply alias to validate_routed_trial; why: main binds this model a value to validate_routed_trial's alias input.
                loaded["router"], alias="model-a", prior_activations=0, expected_delta=1
            # What: complete the validate_routed_trial call with alias and prior activations and expected delta; why: main groups the supplied clauses as one validate_routed_trial call before its value is consumed.
            )
            # What: compute result entry from control plane canary and base and artifacts; why: result upstream model rewrite upstream model rewrite canary base artifacts later reads result entry, so main must retain the computed value under that name.
            result["controlPlane"] = control_plane_canary(base, artifacts)
            # What: compute result entry from upstream model rewrite canary and base and artifacts; why: result selector selector canary base artifacts later reads result entry, so main must retain the computed value under that name.
            result["upstreamModelRewrite"] = upstream_model_rewrite_canary(base, artifacts)
            # What: compute result entry from selector canary and base and artifacts; why: result routing profile routing profile canary base artifacts later reads result entry, so main must retain the computed value under that name.
            result["selector"] = selector_canary(base, artifacts)
            # What: compute result entry from routing profile canary and base and artifacts; why: result trials append direct row later reads result entry, so main must retain the computed value under that name.
            result["routingProfile"] = routing_profile_canary(base, artifacts)
            # What: compute direct raw and direct row from canary and loaded and model a and http and true; why: artifacts direct a sse write bytes direct raw later reads direct raw and direct row, so main must retain the computed value under that name.
            direct_raw, direct_row = canary(f"http://127.0.0.1:{loaded['port']}", "model-a", direct=True)
            # What: preserve the exact artifacts direct a sse write bytes direct raw literal fragment; why: main passes this fragment verbatim through (artifacts / "direct-a.sse").write_bytes(direct_raw), because changing it would alter a protocol payload, serialized fixture, or public message.
            (artifacts / "direct-a.sse").write_bytes(direct_raw)
            # What: preserve the exact artifacts direct a load json write bytes loaded raw literal fragment; why: main passes this fragment verbatim through (artifacts / "direct-a.load.json").write_bytes(loaded_raw), because changing it would alter a protocol payload, serialized fixture, or public message.
            (artifacts / "direct-a.load.json").write_bytes(loaded_raw)
            # What: compute direct row entry from loaded and router; why: direct row expected activation delta later reads direct row entry, so main must retain the computed value under that name.
            direct_row["router"] = loaded["router"]
            # What: compute direct row entry from 1; why: direct row hardware capture hardware base artifacts direct a later reads direct row entry, so main must retain the computed value under that name.
            direct_row["expectedActivationDelta"] = 1
            # What: compute direct row entry from capture hardware and base and artifacts and direct a; why: final engine port direct row hardware engine port later reads direct row entry, so main must retain the computed value under that name.
            direct_row["hardware"] = capture_hardware(base, artifacts, "direct-a")
            # What: compute final engine port from direct row and port and engine and hardware; why: final engine port row hardware engine port later reads final engine port, so main must retain the computed value under that name.
            final_engine_port = direct_row["hardware"]["engine"]["port"]
            # What: preserve the exact result trials append direct row literal fragment; why: main passes this fragment verbatim through result["trials"].append(direct_row), because changing it would alter a protocol payload, serialized fixture, or public message.
            result["trials"].append(direct_row)

            # What: compute cancel raw and cancellation from cancellation canary and base and model a; why: artifacts cancel a partial sse write bytes cancel raw later reads cancel raw and cancellation, so main must retain the computed value under that name.
            cancel_raw, cancellation = cancellation_canary(base, "model-a")
            # What: preserve the exact artifacts cancel a partial sse write bytes cancel raw literal fragment; why: main passes this fragment verbatim through (artifacts / "cancel-a.partial.sse").write_bytes(cancel_raw), because changing it would alter a protocol payload, serialized fixture, or public message.
            (artifacts / "cancel-a.partial.sse").write_bytes(cancel_raw)
            # What: compute result entry from cancellation; why: result concurrency concurrency later reads result entry, so main must retain the computed value under that name.
            result["cancellation"] = cancellation

            # What: compute concurrent rows and concurrency from concurrent canaries and base and model a; why: for index concurrent raw value in enumerate later reads concurrent rows and concurrency, so main must retain the computed value under that name.
            concurrent_rows, concurrency = concurrent_canaries(base, "model-a")
            # What: iterate across enumerate and concurrent rows to perform write bytes and concurrent raw and artifacts and index; why: main repeats the body only while or for the loop header admits an iteration.
            for index, (concurrent_raw, _) in enumerate(concurrent_rows):
                # What: preserve the exact artifacts f concurrent a index sse write bytes literal fragment; why: main passes this fragment verbatim through (artifacts / f"concurrent-a-{index}.sse").write_bytes(concurrent_raw), because changing it would alter a protocol payload, serialized fixture, or public message.
                (artifacts / f"concurrent-a-{index}.sse").write_bytes(concurrent_raw)
            # What: compute result entry from concurrency; why: result trials append row later reads result entry, so main must retain the computed value under that name.
            result["concurrency"] = concurrency
            # What: call save with the declared inputs; why: main invokes save while performing for label alias expected delta in; the call advances that operation through its result or side effect.
            save()

            # What: iterate across the computed value to perform raw and row and canary and base and alias; why: main repeats the body only while or for the loop header admits an iteration.
            for label, alias, expected_delta in (
                # What: apply the warm a model a portion of the enclosing predicate; why: this clause remains in main\'s enclosing expression so its grouping and evaluation order stay intact.
                ("warm-a", "model-a", 0),
                # What: apply the cold b model b portion of the enclosing predicate; why: this clause remains in main\'s enclosing expression so its grouping and evaluation order stay intact.
                ("cold-b", "model-b", 1),
                # What: apply the alternating a model a portion of the enclosing predicate; why: this clause remains in main\'s enclosing expression so its grouping and evaluation order stay intact.
                ("alternating-a", "model-a", 1),
            # What: complete the enclosing predicate collection with warm a and model a and 0 and cold b and model b and 1 and alternating a and model a and 1; why: main groups the supplied clauses as one enclosing predicate collection collection before its value is consumed.
            ):
                # What: compute raw and row from canary and base and alias and false; why: raw expected expected delta later reads raw and row, so main must retain the computed value under that name.
                raw, row = canary(base, alias, direct=False)
                # What: compute row entry from label; why: row loading feedback validate loading feedback later reads row entry, so main must retain the computed value under that name.
                row["scenario"] = label
                # What: compute row entry from validate loading feedback and raw and expected delta and 1; why: row router request json base router status later reads row entry, so main must retain the computed value under that name.
                row["loadingFeedback"] = validate_loading_feedback(
                    # What: supply expected to validate_loading_feedback; why: main binds this expected delta and 1 value to validate_loading_feedback's expected input.
                    raw, expected=expected_delta == 1
                # What: complete the validate_loading_feedback call with expected; why: main groups the supplied clauses as one validate_loading_feedback call before its value is consumed.
                )
                # What: compute row entry from request json and base and 1 and router and status; why: row router alias alias prior activations activation count later reads row entry, so main must retain the computed value under that name.
                row["router"] = request_json(base + "/router/status")[1]
                # What: compute activation count from validate routed trial and row and alias and activation count; why: row router alias alias prior activations activation count later reads activation count, so main must retain the computed value under that name.
                activation_count = validate_routed_trial(
                    # What: supply alias to validate_routed_trial; why: main binds this alias value to validate_routed_trial's alias input.
                    row["router"], alias=alias, prior_activations=activation_count,
                    # What: supply expected delta to validate_routed_trial; why: main binds this expected delta value to validate_routed_trial's expected delta input.
                    expected_delta=expected_delta,
                # What: complete the validate_routed_trial call with alias and prior activations and expected delta; why: main groups the supplied clauses as one validate_routed_trial call before its value is consumed.
                )
                # What: compute row entry from expected delta; why: row hardware capture hardware base artifacts label later reads row entry, so main must retain the computed value under that name.
                row["expectedActivationDelta"] = expected_delta
                # What: preserve the exact artifacts f label sse write bytes raw literal fragment; why: main passes this fragment verbatim through (artifacts / f"{label}.sse").write_bytes(raw), because changing it would alter a protocol payload, serialized fixture, or public message.
                (artifacts / f"{label}.sse").write_bytes(raw)
                # What: preserve the exact artifacts f label metrics write bytes request bytes literal fragment; why: main passes this fragment verbatim through (artifacts / f"{label}.metrics").write_bytes(request_bytes(base + "/metr, because changing it would alter a protocol payload, serialized fixture, or public me.
                (artifacts / f"{label}.metrics").write_bytes(request_bytes(base + "/metrics"))
                # What: compute row entry from capture hardware and base and artifacts and label; why: final engine port row hardware engine port later reads row entry, so main must retain the computed value under that name.
                row["hardware"] = capture_hardware(base, artifacts, label)
                # What: compute final engine port from row and port and engine and hardware; why: final engine port result ttl port later reads final engine port, so main must retain the computed value under that name.
                final_engine_port = row["hardware"]["engine"]["port"]
                # What: preserve the exact result trials append row literal fragment; why: main passes this fragment verbatim through result["trials"].append(row), because changing it would alter a protocol payload, serialized fixture, or public message.
                result["trials"].append(row)
                # What: call save with the declared inputs; why: main invokes save while performing failure raw restored raw failed switch failed switch canary; the call advances that operation through its result or side effect.
                save()
            # What: evaluate and capture failure raw restored raw failed switch failed switch canary; why: the enclosing qualifier uses the captured result in its next validation or artifact step.
            failure_raw, restored_raw, failed_switch = failed_switch_canary(
                # What: apply the base model invalid model a portion of failure raw and restored raw and failed switch; why: main uses this clause to evaluate failure raw and restored raw and failed switch as one grouped value.
                base, "model-invalid", "model-a"
            # What: complete the failed_switch_canary call with base; why: main groups the supplied clauses as one failed_switch_canary call before its value is consumed.
            )
            # What: preserve the exact artifacts failed switch response json write bytes failure raw literal fragment; why: main passes this fragment verbatim through (artifacts / "failed-switch-response.json").write_bytes(failure_raw), because changing it would alter a protocol payload, serialized fixture, or public.
            (artifacts / "failed-switch-response.json").write_bytes(failure_raw)
            # What: preserve the exact artifacts failed switch restored a sse write bytes restored raw literal fragment; why: main passes this fragment verbatim through (artifacts / "failed-switch-restored-a.sse").write_bytes(restored_raw), because changing it would alter a protocol payload, serialized fixture, or pub.
            (artifacts / "failed-switch-restored-a.sse").write_bytes(restored_raw)
            # What: compute result entry from failed switch; why: result re adoption later reads result entry, so main must retain the computed value under that name.
            result["failedSwitch"] = failed_switch

            # What: compute before restart raw and before restart from request json and base and engine and status; why: main consumes before restart raw and before restart during artifacts re adoption before engine json write bytes before restart raw, so before restart raw and before restart value receives the comput.
            before_restart_raw, before_restart = request_json(base + "/engine/status")
            # What: compute old pid and old port from get and before restart and pid and port; why: or not isinstance old pid int or later reads old pid and old port, so main must retain the computed value under that name.
            old_pid, old_port = before_restart.get("pid"), before_restart.get("port")
            # What: gate on old pid and get and isinstance and int and old port before runtime error; why: main admits runtime error only for this predicate and excludes the opposite state.
            if (
                # What: call before_restart.get with running; why: main invokes before_restart.get while performing or not isinstance old pid int or; the call advances that operation through its result or side effect.
                not before_restart.get("running")
                # What: call isinstance with old pid and int; why: main invokes isinstance while performing or not isinstance old port int or; the call advances that operation through its result or side effect.
                or not isinstance(old_pid, int) or old_pid <= 0
                # What: call isinstance with old port and int; why: main consumes the isinstance return value while evaluating or not isinstance(old_port, int) or not 1 <= old_port <= 65535.
                or not isinstance(old_port, int) or not 1 <= old_port <= 65535
            # What: complete the enclosing predicate with if not before restart get running or not isinstance old pid int; why: main groups the supplied clauses as one enclosing predicate expression before its value is consumed.
            ):
                # What: raise RuntimeError for the caller; why:  main stops this rejected path before it can mutate state, dispatch work, or report success.
                raise RuntimeError("pre-restart engine identity is invalid")
            # What: preserve the exact artifacts re adoption before engine json write bytes before restart raw literal fragme; why: main passes this fragment verbatim through (artifacts / "re-adoption-before-engine.json").write_bytes(before_restar, because changing it would alter a protocol payload, serialized fixture.
            (artifacts / "re-adoption-before-engine.json").write_bytes(before_restart_raw)
            # What: compute detached engine from old pid and old port; why: detached engine later reads detached engine, so main must retain the computed value under that name.
            detached_engine = (old_pid, old_port)
            # What: call catalog_path.write_text with native catalog text and model a and model b and args; why: main invokes catalog_path.write_text while performing native catalog text; the call advances that operation through its result or side effect.
            catalog_path.write_text(
                # What: call native_catalog_text with model a and args and model b and args; why: main invokes native_catalog_text while performing args model a args model b invalid model invalid model; the call advances that operation through its result or side effect.
                native_catalog_text(
                    # What: supply invalid model to native_catalog_text; why:  main binds this invalid model value to native_catalog_text's invalid model input.
                    args.model_a, args.model_b, invalid_model=invalid_model,
                    # What: supply api key to native_catalog_text; why: main binds this native api key value to native_catalog_text's api key input.
                    api_key=native_api_key, startup=True,
                # What: complete the native_catalog_text call with invalid model and api key and startup; why: main groups the supplied clauses as one native_catalog_text call before its value is consumed.
                ),
                # What: preserve the exact encoding utf 8 literal fragment; why: main passes this fragment verbatim through encoding="utf-8", because changing it would alter a protocol payload, serialized fixture, or public message.
                encoding="utf-8",
            # What: complete the catalog_path.write_text call with encoding; why: main groups the supplied clauses as one catalog_path.write_text call before its value is consumed.
            )
            # What: call stop_process_group with daemon; why: main invokes stop_process_group while performing daemon; the call advances that operation through its result or side effect.
            stop_process_group(daemon)
            # What: compute daemon from the named fixture input; why: daemon launch daemon log stop serve on exit later reads daemon, so main must retain the computed value under that name.
            daemon = None
            # What: call require_listener_open with old port; why: main invokes require_listener_open while performing daemon launch daemon log stop serve on exit; the call advances that operation through its result or side effect.
            require_listener_open(old_port)
            # What: compute daemon from launch daemon and log and true; why: if daemon is not later reads daemon, so main must retain the computed value under that name.
            daemon = launch_daemon(log, stop_serve_on_exit=True)
            # What: compute adopted router from wait json and base and router and status and 30; why: identity validate re adoption before restart adopted engine adopted router later reads adopted router, so main must retain the computed value under that name.
            adopted_router = wait_json(base + "/router/status", seconds=30)
            # What: compute adopted raw and adopted engine from request json and base and engine and status; why: artifacts re adoption after engine json write bytes adopted raw later reads adopted raw and adopted engine, so main must retain the computed value under that name.
            adopted_raw, adopted_engine = request_json(base + "/engine/status")
            # What: preserve the exact artifacts re adoption after engine json write bytes adopted raw literal fragment; why: main passes this fragment verbatim through (artifacts / "re-adoption-after-engine.json").write_bytes(adopted_raw), because changing it would alter a protocol payload, serialized fixture, or pub.
            (artifacts / "re-adoption-after-engine.json").write_bytes(adopted_raw)
            # What: compute identity from validate re adoption and before restart and adopted engine and adopted router; why: identity later reads identity, so main must retain the computed value under that name.
            identity = validate_re_adoption(before_restart, adopted_engine, adopted_router)
            # What: gate on get and adopted router before runtime error; why: main admits runtime error only for this predicate and excludes the opposite state.
            if adopted_router.get("activeRoutingProfile") != "coding":
                # What: raise RuntimeError for the caller; why:  main stops this rejected path before it can mutate state, dispatch work, or report success.
                raise RuntimeError("startup routing profile was not activated")
            # What: compute readopted raw and readopted completion from canary and base and model a and false; why: artifacts re adoption restored a sse write bytes readopted raw later reads readopted raw and readopted completion, so main must retain the computed value under that name.
            readopted_raw, readopted_completion = canary(base, "model-a", direct=False)
            # What: preserve the exact artifacts re adoption restored a sse write bytes readopted raw literal fragment; why: main passes this fragment verbatim through (artifacts / "re-adoption-restored-a.sse").write_bytes(readopted_raw), because changing it would alter a protocol payload, serialized fixture, or publi.
            (artifacts / "re-adoption-restored-a.sse").write_bytes(readopted_raw)
            # What: gate on get and request json and base before runtime error; why: main admits runtime error only for this predicate and excludes the opposite state.
            if request_json(base + "/router/status")[1].get("activations") != 0:
                # What: raise RuntimeError for the caller; why:  main stops this rejected path before it can mutate state, dispatch work, or report success.
                raise RuntimeError("routed request replaced the re-adopted engine")
            # What: compute result entry from identity and get and readopted completion and startup preload reused resident and startup routing profile; why: result conflicting request conflict later reads result entry, so main must retain the computed value under that name.
            result["reAdoption"] = {
                # What: apply the identity portion of result entry; why: main uses this clause to evaluate result entry as one grouped value.
                **identity,
                # What: map the startup preload reused resident field as true; why: main carries startup preload reused resident through result entry into result conflicting request conflict.
                "startupPreloadReusedResident": True,
                # What: map the startup routing profile field as coding; why: main carries startup routing profile through result entry into result conflicting request conflict.
                "startupRoutingProfile": "coding",
                # What: map the completion passed field as get and readopted completion and true and passed; why: main carries completion passed through result entry into result conflicting request conflict.
                "completionPassed": readopted_completion.get("passed") is True,
                # What: map the passed field as get and readopted completion and true and passed; why: main carries passed through result entry into result conflicting request conflict.
                "passed": readopted_completion.get("passed") is True,
            # What: complete the result entry mapping with startup preload reused resident and startup routing profile and completion passed and passed; why: main groups the supplied clauses as one result entry mapping before its value is consumed.
            }
            # What: compute detached engine from the named fixture input; why: if detached engine is later reads detached engine, so main must retain the computed value under that name.
            detached_engine = None
            # What: evaluate and capture conflict a raw conflict b raw conflict restored raw conflict conflicting request canary; why: the enclosing qualifier uses the captured result in its next validation or artifact step.
            conflict_a_raw, conflict_b_raw, conflict_restored_raw, conflict = conflicting_request_canary(
                # What: apply the base model a model b portion of conflict a raw and conflict b raw and conflict restored raw and conflict; why: main uses this clause to evaluate conflict a raw and conflict b raw and conflict restored raw and conflict as one grouped value.
                base, "model-a", "model-b"
            # What: complete the conflicting_request_canary call with base; why: main groups the supplied clauses as one conflicting_request_canary call before its value is consumed.
            )
            # What: preserve the exact artifacts conflict active a partial sse write bytes conflict a raw literal fragment; why: main passes this fragment verbatim through (artifacts / "conflict-active-a.partial.sse").write_bytes(conflict_a_raw, because changing it would alter a protocol payload, serialized fixture, o.
            (artifacts / "conflict-active-a.partial.sse").write_bytes(conflict_a_raw)
            # What: preserve the exact artifacts conflict waiting b sse write bytes conflict b raw literal fragment; why: main passes this fragment verbatim through (artifacts / "conflict-waiting-b.sse").write_bytes(conflict_b_raw), because changing it would alter a protocol payload, serialized fixture, or public mess.
            (artifacts / "conflict-waiting-b.sse").write_bytes(conflict_b_raw)
            # What: preserve the exact artifacts conflict restored a sse write bytes conflict restored raw literal fragment; why: main passes this fragment verbatim through (artifacts / "conflict-restored-a.sse").write_bytes(conflict_restored_ra, because changing it would alter a protocol payload, serialized fixture.
            (artifacts / "conflict-restored-a.sse").write_bytes(conflict_restored_raw)
            # What: compute result entry from conflict; why: result reload conflict reload conflict canary later reads result entry, so main must retain the computed value under that name.
            result["conflictingRequest"] = conflict
            # What: compute result entry from reload conflict canary and base and catalog path and model a; why: result persistent capacity persistent later reads result entry, so main must retain the computed value under that name.
            result["reloadConflict"] = reload_conflict_canary(
                # What: supply api key to reload_conflict_canary; why: main binds this native api key value to reload_conflict_canary's api key input.
                base, catalog_path, args.model_a, args.model_b, api_key=native_api_key
            # What: complete the reload_conflict_canary call with api key; why: main groups the supplied clauses as one reload_conflict_canary call before its value is consumed.
            )
            # What: compute persistent raw and persistent from persistent capacity canary and base and catalog path and model; why: main consumes persistent raw and persistent during artifacts persistent capacity rejection json write bytes persistent raw, so persistent raw and persistent value receives the computed va.
            persistent_raw, persistent = persistent_capacity_canary(
                # What: supply api key to persistent_capacity_canary; why: main binds this native api key value to persistent_capacity_canary's api key input.
                base, catalog_path, args.model_a, args.model_b, api_key=native_api_key
            # What: complete the persistent_capacity_canary call with api key; why: main groups the supplied clauses as one persistent_capacity_canary call before its value is consumed.
            )
            # What: preserve the exact artifacts persistent capacity rejection json write bytes persistent raw literal fragme; why: main passes this fragment verbatim through (artifacts / "persistent-capacity-rejection.json").write_bytes(persisten, because changing it would alter a protocol payload, serialized fixture.
            (artifacts / "persistent-capacity-rejection.json").write_bytes(persistent_raw)
            # What: compute result entry from persistent; why: result ttl ttl eviction canary later reads result entry, so main must retain the computed value under that name.
            result["persistentCapacity"] = persistent
            # What: compute result entry from ttl eviction canary and base and catalog path and model a; why: final engine port result ttl port later reads result entry, so main must retain the computed value under that name.
            result["ttl"] = ttl_eviction_canary(
                # What: supply api key to ttl_eviction_canary; why: main binds this native api key value to ttl_eviction_canary's api key input.
                base, catalog_path, args.model_a, args.model_b, api_key=native_api_key
            # What: complete the ttl_eviction_canary call with api key; why: main groups the supplied clauses as one ttl_eviction_canary call before its value is consumed.
            )
            # What: compute final engine port from result and port and ttl; why: if final engine port is not later reads final engine port, so main must retain the computed value under that name.
            final_engine_port = result["ttl"]["port"]
            # What: call save with the declared inputs; why: main invokes save while performing result passed; the call advances that operation through its result or side effect.
            save()
            # What: compute result entry from all and len and get and result; why: len result trials later reads result entry, so main must retain the computed value under that name.
            result["passed"] = (
                # What: call len with result and trials; why: main invokes len while performing and all x passed for x; the call advances that operation through its result or side effect.
                len(result["trials"]) == 4
                # What: call all with x and result and passed and trials; why: main invokes all while performing and result get cancellation get passed is; the call advances that operation through its result or side effect.
                and all(x["passed"] for x in result["trials"])
                # What: call operation.get with passed; why: main invokes operation.get while performing and result get concurrency get passed is; the call advances that operation through its result or side effect.
                and result.get("cancellation", {}).get("passed") is True
                # What: call operation.get with passed; why: main invokes operation.get while performing and result get ttl get passed is; the call advances that operation through its result or side effect.
                and result.get("concurrency", {}).get("passed") is True
                # What: call operation.get with passed; why: main invokes operation.get while performing and result get reload conflict get passed is; the call advances that operation through its result or side effect.
                and result.get("ttl", {}).get("passed") is True
                # What: call operation.get with passed; why: main invokes operation.get while performing and result get failed switch get passed is; the call advances that operation through its result or side effect.
                and result.get("reloadConflict", {}).get("passed") is True
                # What: call operation.get with passed; why: main invokes operation.get while performing and result get re adoption get passed is; the call advances that operation through its result or side effect.
                and result.get("failedSwitch", {}).get("passed") is True
                # What: call operation.get with passed; why: main invokes operation.get while performing and result get persistent capacity get passed is; the call advances that operation through its result or side effect.
                and result.get("reAdoption", {}).get("passed") is True
                # What: call operation.get with passed; why: main invokes operation.get while performing and result get conflicting request get passed is; the call advances that operation through its result or side effect.
                and result.get("persistentCapacity", {}).get("passed") is True
                # What: call operation.get with passed; why: main invokes operation.get while performing and result get control plane get passed is; the call advances that operation through its result or side effect.
                and result.get("conflictingRequest", {}).get("passed") is True
                # What: call operation.get with passed; why: main invokes operation.get while performing and result get selector get passed is; the call advances that operation through its result or side effect.
                and result.get("controlPlane", {}).get("passed") is True
                # What: call operation.get with passed; why: main invokes operation.get while performing and result get routing profile get passed is; the call advances that operation through its result or side effect.
                and result.get("selector", {}).get("passed") is True
                # What: call operation.get with passed; why: main consumes the operation.get return value while evaluating and result.get("routingProfile", {}).get("passed") is True.
                and result.get("routingProfile", {}).get("passed") is True
            # What: complete the result entry expression with result passed len result trials equals 4 and all; why: main groups the supplied clauses as one result entry expression before its value is consumed.
            )
    # What: handle base exception by result error repr exc; why: main converts that failure into this concrete recovery, response, or cleanup behavior.
    except BaseException as exc:  # noqa: BLE001 -- cleanup must record interrupts as qualification failures.
        # What: compute result entry from repr and exc; why: result cleanup error repr exc later reads result entry, so  main must retain the computed value under that name.
        result["error"] = repr(exc)
    # What: run if daemon is not on every exit path; why: main performs this cleanup after success, rejection, or exception so resources and accounting cannot remain stranded.
    finally:
        # What: gate on daemon before request json and oserror and value error and httperror and base; why: main admits request json and oserror and value error and httperror and base only for this predicate and excludes the opposite state.
        if daemon is not None:
            # What: capture any daemon-owned engine before shutting down its control plane; why: early failures previously lost the only exact PID and leaked a memory-consuming model process.
            cleanup_engine = running_engine_identity(base)
            # What: establish the handler boundary for the protected operation; why: main routes failures to oserror and value error and httperror and error and urllib while preserving cleanup and success flow.
            try:
                # What: preserve the exact request json base shutdown timeout literal fragment; why: main passes this fragment verbatim through request_json(base + "/shutdown", {}, timeout=45), because changing it would alter a protocol payload, serialized fixture, or public message.
                request_json(base + "/shutdown", {}, timeout=45)
            # What: handle oserror and value error and httperror and error and urllib by pass; why: main converts that failure into this concrete recovery, response, or cleanup behavior.
            except (OSError, ValueError, urllib.error.HTTPError):
                # What: ignore the anticipated exception handled by this branch; why: launch_daemon continues its retry or cleanup path instead of re-raising that transient failure.
                pass
            # What: establish the handler boundary for the protected operation; why: main routes failures to oserror and timeout expired and subprocess and runtime error while preserving cleanup and success flow.
            try:
                # What: call stop_process_group with daemon; why: main invokes stop_process_group while performing if daemon poll is; the call advances that operation through its result or side effect.
                stop_process_group(daemon)
                # What: stop the captured test-owned engine after daemon termination; why: the first daemon intentionally supports re-adoption and therefore does not automatically stop serve on every early failure.
                if cleanup_engine is not None:
                    # What: terminate and verify the exact captured process group and listener; why: subsequent qualification and protected-service restoration require all test-owned unified memory to be released.
                    stop_detached_engine(*cleanup_engine)
                # What: gate on poll and daemon before runtime error; why: main admits runtime error only for this predicate and excludes the opposite state.
                if daemon.poll() is None:
                    # What: raise RuntimeError for the caller; why:  main stops this rejected path before it can mutate state, dispatch work, or report success.
                    raise RuntimeError("temporary daemon process did not exit")
                # What: gate on final engine port before require listener closed and final engine port; why: main admits require listener closed and final engine port only for this predicate and excludes the opposite state.
                if final_engine_port is not None:
                    # What: call require_listener_closed with final engine port; why: main invokes require_listener_closed while performing except oserror subprocess timeout expired as exc; the call advances that operation through its result or side effect.
                    require_listener_closed(final_engine_port)
            # What: handle oserror and timeout expired and subprocess by result cleanup error repr exc; why: main converts that failure into this concrete recovery, response, or cleanup behavior.
            except (OSError, subprocess.TimeoutExpired) as exc:
                # What: compute result entry from repr and exc; why: result cleanup error repr exc later reads result entry, so  main must retain the computed value under that name.
                result["cleanupError"] = repr(exc)
            # What: handle runtime error by if detached engine is; why: main converts that failure into this concrete recovery, response, or cleanup behavior.
            except RuntimeError as exc:
                # What: gate on detached engine before result and repr and exc; why: main admits result and repr and exc only for this predicate and excludes the opposite state.
                if detached_engine is None:
                    # What: compute result entry from repr and exc; why: result cleanup error repr detached exc later reads result entry, so main must retain the computed value under that name.
                    result["cleanupError"] = repr(exc)
                # What: select the remaining branch that performs try; why: main covers the state excluded by the preceding predicate without conflating the two outcomes.
                else:
                    # What: establish the handler boundary for the protected operation; why: main routes failures to oserror and runtime error while preserving cleanup and success flow.
                    try:
                        # What: call stop_detached_engine with detached engine; why: main invokes stop_detached_engine while performing detached engine; the call advances that operation through its result or side effect.
                        stop_detached_engine(*detached_engine)
                        # What: compute detached engine from the named fixture input; why: elif detached engine is not later reads detached engine, so main must retain the computed value under that name.
                        detached_engine = None
                    # What: handle oserror and runtime error by result cleanup error repr detached exc; why: main converts that failure into this concrete recovery, response, or cleanup behavior.
                    except (OSError, RuntimeError) as detached_exc:
                        # What: compute result entry from repr and detached exc; why: result cleanup error repr exc later reads result entry, so main must retain the computed value under that name.
                        result["cleanupError"] = repr(detached_exc)
        # What: gate on detached engine before stop detached engine and oserror and runtime error and detached engine and result; why: main admits stop detached engine and oserror and runtime error and detached engine and result only for this predicate and excludes the opposite state.
        elif detached_engine is not None:
            # What: establish the handler boundary for the protected operation; why: main routes failures to oserror and runtime error while preserving cleanup and success flow.
            try:
                # What: call stop_detached_engine with detached engine; why: main invokes stop_detached_engine while performing except oserror runtime error as exc; the call advances that operation through its result or side effect.
                stop_detached_engine(*detached_engine)
            # What: handle oserror and runtime error by result cleanup error repr exc; why: main converts that failure into this concrete recovery, response, or cleanup behavior.
            except (OSError, RuntimeError) as exc:
                # What: compute result entry from repr and exc; why: result restored later reads result entry, so main must retain the computed value under that name.
                result["cleanupError"] = repr(exc)
        # What: gate on maintenance before base exception and run and wait json and restored raw and value; why: main admits base exception and run and wait json and restored raw and value only for this predicate and excludes the opposite state.
        if maintenance:
            # What: establish the handler boundary for the protected operation; why: main routes failures to base exception while preserving cleanup and success flow.
            try:
                # What: execute subprocess run service start args protected service check True timeout 180; why: the enclosing symbol requires this operation for its concrete qualification or routing path.
                subprocess.run(service + ["start", args.protected_service], check=True, timeout=180)
                # What: preserve the exact wait json args protected url health seconds literal fragment; why: main passes this fragment verbatim through wait_json(args.protected_url + "/health", seconds=300), because changing it would alter a protocol payload, serialized fixture, or public message.
                wait_json(args.protected_url + "/health", seconds=300)
                # What: compute restored raw and from canary and protected url and protected model and args and true; why: artifacts protected restored response sse write bytes restored raw later reads restored raw and, so main must retain the computed value under that name.
                restored_raw, _ = canary(args.protected_url, protected_model, direct=True)
                # What: preserve the exact artifacts protected restored response sse write bytes restored raw literal fragment; why: main passes this fragment verbatim through (artifacts / "protected-restored-response.sse").write_bytes(restored_raw, because changing it would alter a protocol payload, serialized fixtur.
                (artifacts / "protected-restored-response.sse").write_bytes(restored_raw)
                # What: remove the owned watchdog marker after authoritative health and inference; why: normal automatic protection should resume only after restoration is proven.
                if maintenance_marker_owned and maintenance_marker is not None:
                    # What: unlink the exact owned marker; why: a completed maintenance window must not leave watchdog recovery disabled.
                    maintenance_marker.unlink(missing_ok=True)
                    # What: clear marker ownership after removal; why: later cleanup must not repeat or misreport the action.
                    maintenance_marker_owned = False
                # What: compute result entry from true; why: result restore error repr exc later reads result entry, so main must retain the computed value under that name.
                result["restored"] = True
            # What: handle base exception by result restore error repr exc; why: main converts that failure into this concrete recovery, response, or cleanup behavior.
            except BaseException as exc:  # noqa: BLE001 -- cleanup must record interrupts as qualification failures.
                # What: compute result entry from repr and exc; why: return if result get passed and result later reads result entry, so main must retain the computed value under that name.
                result["restoreError"] = repr(exc)
                # What: remove an owned marker after a failed explicit restoration attempt; why: the existing watchdog must regain permission to recover the protected service.
                if maintenance_marker_owned and maintenance_marker is not None:
                    # What: unlink the exact owned marker without masking the restoration error; why: recovery enablement is safer than preserving a stale maintenance lock.
                    maintenance_marker.unlink(missing_ok=True)
                    # What: clear marker ownership after emergency release; why: saved state must reflect that watchdog suppression no longer remains.
                    maintenance_marker_owned = False
        # What: call save with the declared inputs; why: main invokes save while performing return if result get passed and result; the call advances that operation through its result or side effect.
        save()
    # What: return get and result and 0 and 1 and passed from main; why: main exposes get and result and 0 and 1 and passed so its caller can continue with the function\'s computed outcome.
    return 0 if result.get("passed") and result["restored"] and "cleanupError" not in result else 1


# What: gate on name before system exit and main; why: qualify_native_router admits system exit and main only for this predicate and excludes the opposite state.
if __name__ == "__main__":
    # What: raise SystemExit for the caller; why: qualify_native_router stops this rejected path before it can mutate state, dispatch work, or report success.
    raise SystemExit(main())
