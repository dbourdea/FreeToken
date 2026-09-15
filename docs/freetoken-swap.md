# freetoken-swap: native, safe model routing

`freetoken-swap` is the native `ft daemon` routing mode. A client sends a
supported FreeToken OpenAI- or Anthropic-compatible request to the daemon's
stable URL with an allowlisted catalog alias in JSON `model`. The daemon alone
admits the request, starts or reuses one `ft serve` child, waits for its
generation-aware readiness, and proxies ordinary and SSE bytes unchanged. Its
lease stays active until the response closes, so another model cannot replace a
stream in flight. The same owner performs accounting, graceful drain/abort,
process-identity checks, cleanup, rollback, and re-adoption; **do not** put
llama-swap or another supervisor in front of the same FreeToken child.

Legacy `/engine/start`, `/engine/stop`, `/engine/switch`, and profile variants
remain available only when the router does not own or admit work. They reserve
the same lifecycle barrier for their complete transaction, so a routed request
waits rather than racing a manual process operation. A manual stop may supersede
a manual operation blocked in readiness; its newer manager intent invalidates
stale rollback, and the older token cannot clear the stop's barrier. If the
manual HTTP client disconnects, the barrier remains held until the complete
executor-backed lifecycle transaction, including required rollback, terminates.
Daemon shutdown uses the same coordinator: it closes admission, wakes queued
requests with a stable shutdown error, drains active leases and lifecycle work,
then permanently stops the manager-owned child. A failed stop reopens admission;
a successful stop requests daemon exit even if the initiating client disconnects.
OS- and lifespan-triggered exit also quiesces this coordinator. The default
detach policy drains ownership and leaves the exact persisted child available
for re-adoption; `--stop-serve-on-exit` drains and permanently stops it instead.
Catalog reload binds profile lookup, priority ticketing, and dynamic-port
selection atomically. Reload is rejected while admission or lifecycle work is
pending, so an activating or queued request cannot change definitions mid-flight.

The read-only, pinned llama-swap source remains a compatibility reference and
an optional separate deployment mode, not a runtime dependency. That direct
mode cannot gain this daemon's accounting guarantees. See the
[parity matrix](freetoken-swap-parity-matrix.md) for the source-backed
capability classification and [research](freetoken-swap-research.md) for
bounded qualification evidence and limits.

The catalog is TOML and is optional. Start the daemon with `--catalog` or set `FREETOKEN_SWAP_CATALOG`:

```toml
[router]
send_loading_state = true
preload_model = "qwen-coder-compatible"
startup_routing_profile = "coding"
# Matching direct-upstream assets return 409 instead of cold-loading. This
# suffix-only safe subset defaults to js/json/css/png/gif/jpg/jpeg/ico/txt.
upstream_no_activation_suffixes = [".js", ".json", ".css", ".png"]
# Activity metadata is always bounded and body-free. Captures are disabled by
# default; enabling them retains redacted bodies in memory only.
activity_max_entries = 1000
capture_buffer_mb = 0
activity_session_headers = ["X-Session-ID", "X-Litellm-Session-Id"]
performance_disabled = false
performance_every_s = 5

[models.qwen-coder]
model = "/models/Qwen3-Coder-30B-A3B-Q4_K_M.gguf"
port = 1922
args = ["--max-seq-len-override", "4096", "--num-tokens", "4096"]
description = "GMKtek EVO-X2 candidate coding profile"
name = "Qwen coder"
aliases = ["qwen-coder-compatible"]
concurrency_limit = 2
ready_timeout_s = 300
check_endpoint = "/ready"
proxy = "http://127.0.0.1:${PORT}"
use_model_name = "qwen-coder"
upstream_timeout_s = 600
send_loading_state = false

[models.qwen-coder.metadata]
tier = "candidate"
family = "qwen"

[models.qwen-coder.capabilities]
in = ["text"]
out = ["text"]
tools = true
context = 4096

[models.qwen-coder.set_fields]
"max_tokens?" = 4096
"chat_template_kwargs.enable_thinking?" = true

[models.qwen-coder.set_fields_by_id."qwen-coder:high"]
"chat_template_kwargs.reasoning_effort" = "high"

[models.qwen-chat]
model = "/models/Qwen3.5-27B-Q4_K_M.gguf"
args = ["--max-seq-len-override", "4096", "--num-tokens", "4096"]

[selectors.preferred-chat]
strategy = "warm"
targets = ["qwen-coder-compatible", "qwen-chat"]
name = "Preferred chat model"
description = "Reuse a ready target, otherwise start the first target"

[selectors.preferred-chat.metadata]
tier = "stable"

[profiles.coding]
description = "Coding-focused routing mode"

[profiles.coding.pins]
llm-code = "preferred-chat"
llm-plan = "qwen-coder:high"
image-gen = ""
```

```bash
ft daemon --catalog /etc/freetoken/models.toml
ft daemon models
ft daemon routing-profiles
ft daemon activate-routing-profile coding
ft daemon clear-routing-profile
ft daemon start-profile qwen-coder
ft daemon switch-profile qwen-chat
ft daemon health
```

`GET /router/profiles`, `PUT /router/profiles/active`,
`POST /engine/start-profile`, and `POST /engine/switch-profile` expose explicit
control-plane operations. They require `X-FT-Token` whenever the daemon has a
token configured. The start/switch endpoints select a concrete model lifecycle
profile; the PUT endpoint activates or clears a runtime routing profile.
`GET /models` is instead the pinned public-model-list alias of `GET /v1/models`
and uses catalog API-key authentication. Use `switch-profile --force` only for
the same recovery case as `ft daemon switch --force`: the final accounting
receipt may be incomplete when a failed engine cannot be observed.

Model lifecycle entries accept allowlisted `model`, `port`, `args`, `description`, `aliases`,
`unlisted`, readiness, TTL/unload, priority, group, and safe JSON request-filter
fields. Optional `use_model_name` gives the same profile a distinct model name
for outbound JSON requests without changing its configured or requested routing
identity. Optional `name` and JSON-compatible `metadata` provide display-only
model-list information; canonical and listed alternate IDs share those values.
Router-owned `type`, `aliases`, and `modelID` metadata wins over conflicting
operator keys, and declared capabilities own their rendered architecture,
capability, parameter, and context fields. A nested `capabilities` table may declare `in`/`out`
text modalities, `tools`, and a nonnegative `context` length for compatible
model-list clients. This metadata does not enable model behavior: operators
must advertise tools only when the model and chat template actually support
them. Unsupported image, audio, video, and reranker claims are rejected rather
than fabricated. Alternate IDs resolve to the same canonical profile and
resident process. Alias names must be unique and cannot collide with canonical
profile names. Canonical and alternate model IDs may use slash-separated safe
segments such as `organization/model` and colon variants such as `model:high`;
empty, traversal-like, and non-ASCII
segments are rejected, and the complete ID is limited to 128 characters.
Group names and each dot-delimited request-field segment retain the narrower
safe-name grammar. An unlisted profile and all its aliases remain routable and
manageable but are omitted from `GET /v1/models`. Set
`router.include_aliases_in_list = true` to list aliases for visible profiles;
canonical visible IDs are always listed. `args`
is passed as an argument vector to `ft serve`; it is never interpreted by a
shell. A profile cannot set `--model` or `--port` in `args`, because those
fields are owned by the supervisor and are part of its conflict and re-adoption
identity. The model files and catalog remain local operational configuration,
not repository content.

Runtime routing profiles are named, atomically selected maps under
`[profiles.<name>.pins]`. A pin replaces a client model ID before aliases,
selectors, and target filters; an empty target disables that ID. Pins may
target a configured canonical ID, alternate ID, or selector, allowing one
profile switch to change several stable client names together. No routing
profile is active by default; `router.startup_routing_profile` selects one
validated profile before serving. Catalog reload still clears runtime pinning.
Active non-disabled pins
that do not shadow configured model/alias/selector IDs appear in the public
model listing with `meta.freetoken.type = "profile"`; disabled pins are omitted.
Profile pins also use longest-prefix replacement on `/upstream/` paths, but a
pin that targets a selector remains invalid there because selectors are not
direct-upstream IDs. Concrete load/unload management ignores active pin maps.

`router.preload_model` accepts one concrete canonical or alternate ID, resolves
aliases during catalog validation, and acquires that model through the same
readiness/accounting/rollback path during daemon startup. The singleton limit
matches native one-resident capacity; selectors and unknown IDs are rejected.
Use a singleton persistent group when the preloaded model must remain resident
until explicit unload.

Selectors are inference-only virtual model IDs. `pin` always resolves to its
first ordered target. `warm` resolves to the first readiness-gated resident
target, then the first target already activating, and otherwise falls back to
the first target. Resolution rewrites the request's top-level `model` to the
selected canonical or alternate target before that target's ordered request
filters run. Selector IDs appear in `/v1/models` unless `unlisted = true`;
their loaded status follows only the first target for `pin` and any target for
`warm`. Optional JSON-compatible selector `metadata` is nested under
`meta.freetoken`, while router-owned `type`, `strategy`, and `targets` keys
cannot be overridden. Targets must be configured profiles or aliases, selector
chaining is rejected, and `/upstream/{model-id}` plus named unload remain
concrete profile/alias controls. The `spillover` strategy requires concurrent
multi-resident or peer capacity and is therefore rejected under FreeToken's
explicit one-resident policy rather than emulated inaccurately.

`drop_fields` removes configured dot-delimited object paths. `set_fields`
forces JSON-compatible values; a quoted key ending in `?` sets the value only
when that path is absent, so explicit `null`, zero, and false remain client
choices. `set_fields_by_id` runs last and can override global assignments for a
canonical or alternate requested ID. Its table names automatically become
aliases of the same resident model, subject to the normal collision checks.
When configured, `use_model_name` first rewrites the outbound top-level `model`;
filters then run in `drop_fields`, `set_fields`, and `set_fields_by_id` order and
cannot directly configure that protected field. The by-ID table still keys on
the client-facing selected/requested ID rather than the upstream override. For
a selector request without an explicit override, the router first replaces the
field with the resolved target. All filters apply to the exact acquired target
snapshot, including JSON direct-upstream requests; non-JSON direct bodies and
profiles with no rewrite or filters remain byte-exact.
An active profile cannot have its filter policy changed by catalog reload.
There is no expression evaluator or lifecycle shell-hook language.

Set `port = 0` to request a kernel-selected loopback port on every cold native
activation. The daemon records the concrete assigned port and uses that same
target for child identity, readiness, proxying, accounting, and re-adoption;
an already resident dynamic profile keeps its port until it is unloaded.
Dynamic binding occurs only when a request reaches the head of admission, so
simultaneous cold requests for one profile share the single committed target.
`models.<name>.check_endpoint` selects a safe absolute readiness path and
defaults to `/health`; the private native qualifier uses `/ready`. A non-health
endpoint follows pinned HTTP-success semantics while the daemon still checks
the exact managed PID before and after every probe. `models.<name>.proxy` may
add a safe path prefix to `http://127.0.0.1:${PORT}`. The `${PORT}` placeholder
is mandatory, and other schemes, hosts, explicit ports, credentials, queries,
fragments, empty path segments, and traversal are rejected. This deliberately
keeps proxy traffic on the exact manager-owned child rather than creating an
arbitrary SSRF or split-ownership target.

`models.<name>.upstream_timeout_s` overrides `router.upstream_timeout_s` for
the acquired profile's fresh loopback HTTP connection and response reads. The
exact admitted profile snapshot supplies the timeout for both ordinary and SSE
requests. TLS-handshake and pooled keepalive timeout knobs from the reference
are inapplicable because native targets are restricted to fresh manager-owned
plain-HTTP loopback connections.

Each profile admits at most 10 reserved requests by default across its canonical
and alternate IDs. Set `models.<name>.concurrency_limit` to a positive override.
`router.global_concurrency_limit = 0` leaves the global cap disabled; a positive
value caps all active, queued, and activating routed requests. Capacity is
reserved before loading, so excess work is rejected immediately with HTTP 429,
`Retry-After: 1`, and `error.type=concurrency_limit` rather than consuming a
queue slot or launching an engine. Status and Prometheus expose reserved work.

`router.send_loading_state = true` enables optional cold-load feedback for
strictly streaming `POST /v1/chat/completions` requests. A profile can override
the global setting with `models.<name>.send_loading_state = true` or `false`.
After concurrency admission, a cold request receives HTTP 200 SSE reasoning
deltas with loading and queue-position text until the readiness-gated engine is
available, followed by the real upstream stream. Admission rejection remains a
normal HTTP 429 JSON response. Once loading SSE has committed HTTP 200, a later
activation or connection failure is delivered as an in-band `error` event and
terminated with `data: [DONE]`. The default is disabled, and warm, non-chat, and
non-streaming requests retain the ordinary byte/status/header-preserving proxy.

The native capacity policy is deliberately one resident child. Therefore a
nonpersistent group must use `swap = true, exclusive = true`; a persistent
protected slot must be a one-member group with `swap = false, exclusive = true`.
Catalog reload rejects llama-swap coexistence configurations instead of silently
pretending that multiple FreeToken engines are resident.

When started with `--catalog`, the daemon polls it once per second by default.
`--catalog-watch-interval 0` disables that watcher. A changed catalog is parsed
and fully validated before atomic installation; malformed files and active
profile redefinitions are rejected without disturbing the running child. The
watcher's last result appears in `GET /router/status` and its sanitized events
appear in `/router/logs`.

## Native router API

The routed inference surface is `GET /v1/models` plus `POST /v1/chat/completions`,
`/v1/completions`, `/v1/responses`, `/v1/messages`, and
`/v1/messages/count_tokens`. Canonical and alternate IDs share one canonical
residency, capability metadata, and loaded/unloaded listing status while
preserving the client's request body. Readiness-gated activation is reported as
loaded, and stale child identity is reported as unloaded. The public listing includes descriptions but
never model paths or launch arguments. Declared text modalities, tool calling,
and context length use the pinned llama-swap listing fields. Unknown IDs return
a stable 404; unsupported FreeToken modalities are not fabricated. `GET /router/status`, `/router/models`,
`/router/profiles`, `/router/requests`, and `/metrics` expose configured and
resident state, capacity, queues, lifecycle timing, response bytes and proxy
byte rate, concurrency reservations, cancellation, and eviction signals. These transport measurements do
not substitute for live engine token-throughput qualification.
Browser clients receive the pinned compatibility contract: any `OPTIONS`
preflight is answered without lifecycle side effects, requested header names
are restricted to valid HTTP tokens, and authenticated `GET /v1/models`
reflects its `Origin`. Preflight never authorizes the corresponding request;
inference and management routes still enforce their configured keys.
`activeIdentityMatchesEngine` makes a stale or out-of-band child visible rather
than reporting its configured alias as resident.
`PUT /router/profiles/active`, `POST /router/unload`, `/router/reload`, and
`/router/requests/{id}/cancel` control idle eviction, atomic catalog reload,
and a queued, connecting, or active request. The request list exposes reserved
IDs from admission through stream completion, so an operator can cancel any
owned phase. An unload body containing `name` targets that profile;
an omitted body unloads all residents, which is exactly the current resident
under the explicit one-engine capacity policy. `POST /router/load` activates a named profile through
the same native lifecycle transaction without fabricating an inference request.
`GET /router/logs?since=` is a bounded SSE event stream;
it records only event type, alias, registered route template, status,
cancellation state, and response byte count—never prompts, request bodies,
headers, concrete URL paths, query strings, model paths, or API keys.
Router Bearer, Basic-password, and `X-Api-Key` credentials plus the daemon
`X-FT-Token` are terminated at the router and never forwarded to the engine;
ordinary non-hop-by-hop application headers are otherwise preserved.

FreeToken's legacy `POST /generate` body has no model identifier, so exposing it
at the stable router URL would require an implicit default and violate explicit
model-ID ownership. It is therefore intentionally absent there. Clients that
need this legacy protocol must select a configured alias explicitly with
`POST /upstream/{profile}/generate`; that guarded route still acquires the same
router lease and preserves the request and SSE response bytes.

`GET /ready` is an unauthenticated, side-effect-free readiness probe for the
stable router URL. It returns 200 only while a resident routed engine reports
FreeToken's `status=ok` and `maintenance=serving` **and** still exactly matches
the resident alias's model, port, and argument vector. Identity and fresh
health are checked behind the admission barrier, so a conflicting swap cannot
begin between the identity snapshot and a successful response; the probe never
cold-loads a profile. The stateless backend's `GET /v1/responses/{id}` and
response-specific cancel endpoints are authenticated at the stable daemon URL
and return the backend's documented `invalid_request_error` 404 without loading
a model. They are therefore compatibility endpoints, not routing or lifecycle
operations.

`GET /ui/` serves a dependency-free local management shell. It embeds no
catalog values, paths, keys, or machine data; the operator enters a bearer key
for the current browser session and it calls the authenticated router APIs.
The UI presents configured/resident models, load/unload/reload controls, router
status, and the privacy-preserving `GET /router/hardware` memory view. Authenticated
`GET /router/activity`, `/router/activity/stats`, and `/router/captures/{id}`
provide bounded diagnostics. Activity rows never contain bodies or headers.
Real daemon runs persist them as bounded, fsynced JSONL under the daemon-owned
state directory; the file is atomically compacted and corrupt/truncated rows
fail closed. API responses expose persistence health without exposing its path.
Captures are disabled unless `router.capture_buffer_mb` is positive, live only
in memory, cap each response at 1 MiB, obey the total serialized-byte budget,
and redact Authorization, proxy authorization, cookies, `X-Api-Key`,
`X-FT-Token`, and custom token/secret/API-key header names. Bodies use Base64
fields for binary fidelity and are never persisted. The UI lists body-free
activity and fetches a capture only after an explicit click. Configured session
headers are validated, may not name credentials, and are stored/displayed only
as stable 16-character SHA-256 labels; raw identifiers are never retained. MCP
and Tailcat remain deferred product expansions.

`GET /api/performance` and `/router/performance` expose at most one hour of
periodic samples at `router.performance_every_s` (minimum five seconds).
The compatible envelope contains `sys_stats` and `gpu_stats`; native
`sys_stats` rows are explicitly scoped to the owned engine process tree and
contain only RAM/VRAM bytes, availability, and probe source. `gpu_stats` is
empty because FreeToken does not fabricate adapter-wide utilization,
temperature, power, or fan data from process memory. Strict RFC3339 `after`
filtering is supported. The history is memory-only, authenticated, bounded,
and disabled with `router.performance_disabled = true`.

When `router.api_keys` is configured, authentication accepts an
`Authorization: Bearer` value, an HTTP Basic password, or `X-Api-Key` for
inference and, absent a daemon token, router management. Explicit Authorization
credentials take precedence over `X-Api-Key`; malformed Basic may fall back to
it. Invalid requests include a `WWW-Authenticate` challenge. An explicit daemon
`X-FT-Token` remains the dedicated control-plane override. The guarded
`/upstream/{model-id}/...` passthrough uses the same lease but refuses a direct
engine `prepare-stop`, which only the lifecycle owner may invoke. For
slash-namespaced IDs, the longest configured canonical or alternate ID wins;
encoded model separators and the remaining escaped path and query are
forwarded without decoding. By default, direct-upstream paths ending in
`.js`, `.json`, `.css`, `.png`, `.gif`, `.jpg`, `.jpeg`, `.ico`, or `.txt`
return HTTP 409 while the selected model is unloaded, rather than activating
an engine for a speculative asset request. They proxy normally when that exact
model is resident. Configure the bounded, dot-suffix-only
`router.upstream_no_activation_suffixes` list, or set it to `[]` to disable the
guard. Matching is case-sensitive and excludes the query string.

These are illustrative paths, not a list of qualified models. In particular, dense Qwen GGUF support requires a compatible AMD/model-loader branch and cannot be inferred from this control-plane PR.

After a profile launch, the daemon polls uncached engine health, verifies the process identity again after each probe, and waits for `status=ok` and `maintenance=serving`. Readiness failure returns HTTP 503. The client returns a nonzero exit code and defaults to a 1920-second transport budget, covering two maximum 900-second readiness windows plus lifecycle overhead. A user-specified client timeout still takes precedence.

For `switch-profile`, readiness failure attempts to restore the exact previous engine and probes its readiness using a second window of the requested profile's `ready_timeout_s`. The response remains HTTP 503 because the requested replacement failed, with a separate `rollback.readiness` result. Recovery is single-use and invalidated by any newer start, stop, switch, or shutdown. HTTP probing releases the lifecycle lock and runs in the proxy pool, so an operator can stop a loading engine without waiting for the readiness timeout. Accounting failure during recovery preserves the failed engine instead of silently forcing cleanup. An initial `start-profile` or a switch with no previous engine leaves the failed process managed for diagnosis. These policies do not change the direct llama-swap supervisor.

If a replacement launch raises before an owned child exists, the daemon attempts to relaunch the previous model with its exact port and arguments, under the same lifecycle transaction. Both switch endpoints return HTTP 503 with `code=switch_launch_failed`, the original accounting receipt, and a `rollback` result. `rollback.launched` means only that the recovery process launched, not that it is ready. A failed recovery is reported explicitly. Accounting failures before stop preserve the original engine; a post-spawn failure that leaves an owned child does not trigger a second launch. These safeguards apply to daemon switches, not the separate direct llama-swap supervisor.

FreeToken's `/health` remains a backwards-compatible diagnostic endpoint and can return HTTP 200 while loading or failed. `/ready` returns HTTP 503 for loading, failure, or maintenance, and HTTP 200 only when accepting requests. Configure llama-swap with `checkEndpoint: /ready`, never `/health` or `/v1/models` as a substitute.

Use `ft serve` or `python -m freetoken.cli serve` in a process command. The legacy `python -m freetoken` entrypoint does not accept the `serve` subcommand. Use a revision-specific `TORCH_EXTENSIONS_DIR` and prebuild native GGUF kernels before a maintenance window so an abandoned shared build lock cannot stall model initialization. For SSE token metrics, clients should request `stream_options: {"include_usage": true}`.

The opt-in native maintenance harness `benchmarks/swap/qualify_native_router.py`
generates a private API key scoped only to its temporary daemon origin. Its
acceptance result requires 401 responses without that key and authenticated
Bearer, Basic-password, `X-Api-Key`, model/profile inventory, Prometheus metrics,
bounded router-log SSE, and authenticated periodic-performance history with a
positive available owned-process RAM/VRAM sample and no PID/model/path fields;
the key, catalog, headers, and raw captures are never publication artifacts.

## Cancellation qualification

The opt-in Linux harness `benchmarks/swap/qualify.py --cancellation` adds a live disconnect gate to its maintenance-window run. It reads SSE incrementally, verifies that generation is active, closes the response after the first content delta, and polls backend statistics through `/upstream/model-a/v1/stats`. Passing requires the same backend instance to become idle without increasing the normal-completion count. A backend restart, an already-finished response, or a missing terminal abort fails the gate. It then checks fresh A-to-B-to-A streaming completions. Prefix bytes, backend snapshots, first-content timing, abort latency, and recovery responses are private artifacts.

The gate passed against the real Qwen3.6 GPU workload on GMKtek EVO-X2 in an approved maintenance window. The same backend changed from one active request to zero, with its normal-completion count unchanged. Observed first content was 0.368 seconds and terminal abort was observed 0.254 seconds after disconnect. Post-cancellation A-to-B-to-A streaming, concurrent routing, idle eviction, and protected-service restoration also passed. This is one bounded cancellation case, not a cancellation endurance benchmark. Use `--extended` as well to retain concurrent-request and TTL gates. Existing mandatory source, model, protected-service, and artifact arguments still apply. The current harness additionally requires the exact operating-system hostname in `--expected-hostname` before artifact creation or service inspection; `--allow-maintenance` is not a substitute for operator approval.

## Native model-failure recovery qualification

`benchmarks/swap/qualify_native_recovery.py` exercises the actual daemon profile endpoints with real FreeToken child processes. It starts the supplied model, verifies generation, switches to a deliberately invalid GGUF fixture in its private artifact directory, checks the HTTP 503 response and automatic recovery readiness, then verifies streamed generation from the restored model. The real Qwen3.6 run passed after the loader reported `GGUF magic invalid`. The original engine's sealed accounting receipt was complete; the failed loader's crash receipt was explicitly degraded with unknown token totals. Cleanup and restoration of the protected llama.cpp workload passed.

The harness accepts separate `--source` and `--daemon-source` paths so the AMD runtime and the swap feature branch can be tested together without modifying a live checkout. `--extensions-dir` must identify a private cache prebuilt from the selected runtime source. Required arguments also include `--python`, `--model`, `--protected-service`, `--protected-url`, `--artifacts`, `--expected-hostname`, and `--allow-maintenance`. The exact hostname must match before artifact creation or service inspection; mismatch errors do not disclose it. The fixture never replaces an existing model. Raw logs and result files contain private deployment details and must not be published unreviewed.

## Provenance and scope

The design was informed by [mostlygeek/llama-swap](https://github.com/mostlygeek/llama-swap), checked out locally at `41ec321b6216d838488b2a7d936274ed227c0c5e` on 2026-09-10. llama-swap is MIT licensed (`LICENSE.md`). No llama-swap or llama.cpp code is vendored, modified, or submitted by this feature. FreeToken remains the sole change and pull-request target.
