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

The read-only, pinned llama-swap source remains a compatibility reference and
an optional separate deployment mode, not a runtime dependency. That direct
mode cannot gain this daemon's accounting guarantees. See the
[parity matrix](freetoken-swap-parity-matrix.md) for the source-backed
capability classification and [research](freetoken-swap-research.md) for
bounded qualification evidence and limits.

The catalog is TOML and is optional. Start the daemon with `--catalog` or set `FREETOKEN_SWAP_CATALOG`:

```toml
[models.qwen-coder]
model = "/models/Qwen3-Coder-30B-A3B-Q4_K_M.gguf"
port = 1922
args = ["--max-seq-len-override", "4096", "--num-tokens", "4096"]
description = "GMKtek EVO-X2 candidate coding profile"
ready_timeout_s = 300

[models.qwen-chat]
model = "/models/Qwen3.5-27B-Q4_K_M.gguf"
args = ["--max-seq-len-override", "4096", "--num-tokens", "4096"]
```

```bash
ft daemon --catalog /etc/freetoken/models.toml
ft daemon models
ft daemon start-profile qwen-coder
ft daemon switch-profile qwen-chat
ft daemon health
```

`GET /models`, `POST /engine/start-profile`, and `POST /engine/switch-profile` expose explicit control-plane operations. They require `X-FT-Token` whenever the daemon has a token configured. Use `switch-profile --force` only for the same recovery case as `ft daemon switch --force`: the final accounting receipt may be incomplete when a failed engine cannot be observed.

Profiles accept allowlisted `model`, `port`, `args`, `description`, readiness,
TTL/unload, priority, group, and safe top-level request-filter fields. `args`
is passed as an argument vector to `ft serve`; it is never interpreted by a
shell. A profile cannot set `--model` or `--port` in `args`, because those
fields are owned by the supervisor and are part of its conflict and re-adoption
identity. The model files and catalog remain local operational configuration,
not repository content.

Set `port = 0` to request a kernel-selected loopback port on every cold native
activation. The daemon records the concrete assigned port and uses that same
target for child identity, readiness, proxying, accounting, and re-adoption;
an already resident dynamic profile keeps its port until it is unloaded.

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
`/v1/messages/count_tokens`. Unknown aliases return a stable 404; unsupported
FreeToken modalities are not fabricated. `GET /router/status`, `/router/models`,
`/router/profiles`, `/router/requests`, and `/metrics` expose configured and
resident state, capacity, queues, lifecycle timing, response bytes and proxy
byte rate, cancellation, and eviction signals. These transport measurements do
not substitute for live engine token-throughput qualification.
`activeIdentityMatchesEngine` makes a stale or out-of-band child visible rather
than reporting its configured alias as resident.
`POST /router/unload`, `/router/reload`, and
`/router/requests/{id}/cancel` control idle eviction, atomic catalog reload,
and an active request. `POST /router/load` activates a named profile through
the same native lifecycle transaction without fabricating an inference request.
`GET /router/logs?since=` is a bounded SSE event stream;
it records only event type, alias, registered route template, status,
cancellation state, and response byte count—never prompts, request bodies,
headers, concrete URL paths, query strings, model paths, or API keys.
Router bearer keys and the daemon `X-FT-Token` are terminated at the router and
never forwarded to the engine; ordinary non-hop-by-hop application headers are
otherwise preserved.

`GET /ready` is an unauthenticated, side-effect-free readiness probe for the
stable router URL. It returns 200 only while a resident routed engine reports
FreeToken's `status=ok` and `maintenance=serving` **and** still exactly matches
the resident alias's model, port, and argument vector; it never cold-loads a
profile. The stateless backend's `GET /v1/responses/{id}` and response-specific
cancel endpoints always return its documented 404 and are therefore not routing
or lifecycle operations.

`GET /ui/` serves a dependency-free local management shell. It embeds no
catalog values, paths, keys, or machine data; the operator enters a bearer key
for the current browser session and it calls the authenticated router APIs.
The UI presents configured/resident models, load/unload/reload controls, router
status, and the privacy-preserving `GET /router/hardware` memory view. Captures,
MCP, and Tailcat remain outside FreeToken's current product scope.

When `router.api_keys` is configured, bearer authentication protects inference
and all router management endpoints. An explicit daemon `X-FT-Token` remains
the dedicated control-plane override. The guarded
`/upstream/{profile}/...` passthrough uses the same lease but refuses a direct
engine `prepare-stop`, which only the lifecycle owner may invoke.

These are illustrative paths, not a list of qualified models. In particular, dense Qwen GGUF support requires a compatible AMD/model-loader branch and cannot be inferred from this control-plane PR.

After a profile launch, the daemon polls uncached engine health, verifies the process identity again after each probe, and waits for `status=ok` and `maintenance=serving`. Readiness failure returns HTTP 503. The client returns a nonzero exit code and defaults to a 1920-second transport budget, covering two maximum 900-second readiness windows plus lifecycle overhead. A user-specified client timeout still takes precedence.

For `switch-profile`, readiness failure attempts to restore the exact previous engine and probes its readiness using a second window of the requested profile's `ready_timeout_s`. The response remains HTTP 503 because the requested replacement failed, with a separate `rollback.readiness` result. Recovery is single-use and invalidated by any newer start, stop, switch, or shutdown. HTTP probing releases the lifecycle lock and runs in the proxy pool, so an operator can stop a loading engine without waiting for the readiness timeout. Accounting failure during recovery preserves the failed engine instead of silently forcing cleanup. An initial `start-profile` or a switch with no previous engine leaves the failed process managed for diagnosis. These policies do not change the direct llama-swap supervisor.

If a replacement launch raises before an owned child exists, the daemon attempts to relaunch the previous model with its exact port and arguments, under the same lifecycle transaction. Both switch endpoints return HTTP 503 with `code=switch_launch_failed`, the original accounting receipt, and a `rollback` result. `rollback.launched` means only that the recovery process launched, not that it is ready. A failed recovery is reported explicitly. Accounting failures before stop preserve the original engine; a post-spawn failure that leaves an owned child does not trigger a second launch. These safeguards apply to daemon switches, not the separate direct llama-swap supervisor.

FreeToken's `/health` remains a backwards-compatible diagnostic endpoint and can return HTTP 200 while loading or failed. `/ready` returns HTTP 503 for loading, failure, or maintenance, and HTTP 200 only when accepting requests. Configure llama-swap with `checkEndpoint: /ready`, never `/health` or `/v1/models` as a substitute.

Use `ft serve` or `python -m freetoken.cli serve` in a process command. The legacy `python -m freetoken` entrypoint does not accept the `serve` subcommand. Use a revision-specific `TORCH_EXTENSIONS_DIR` and prebuild native GGUF kernels before a maintenance window so an abandoned shared build lock cannot stall model initialization. For SSE token metrics, clients should request `stream_options: {"include_usage": true}`.

## Cancellation qualification

The opt-in Linux harness `benchmarks/swap/qualify.py --cancellation` adds a live disconnect gate to its maintenance-window run. It reads SSE incrementally, verifies that generation is active, closes the response after the first content delta, and polls backend statistics through `/upstream/model-a/v1/stats`. Passing requires the same backend instance to become idle without increasing the normal-completion count. A backend restart, an already-finished response, or a missing terminal abort fails the gate. It then checks fresh A-to-B-to-A streaming completions. Prefix bytes, backend snapshots, first-content timing, abort latency, and recovery responses are private artifacts.

The gate passed against the real Qwen3.6 GPU workload on GMKtek EVO-X2 in an approved maintenance window. The same backend changed from one active request to zero, with its normal-completion count unchanged. Observed first content was 0.368 seconds and terminal abort was observed 0.254 seconds after disconnect. Post-cancellation A-to-B-to-A streaming, concurrent routing, idle eviction, and protected-service restoration also passed. This is one bounded cancellation case, not a cancellation endurance benchmark. Use `--extended` as well to retain concurrent-request and TTL gates. Existing mandatory source, model, protected-service, and artifact arguments still apply; `--allow-maintenance` is not a substitute for operator approval.

## Native model-failure recovery qualification

`benchmarks/swap/qualify_native_recovery.py` exercises the actual daemon profile endpoints with real FreeToken child processes. It starts the supplied model, verifies generation, switches to a deliberately invalid GGUF fixture in its private artifact directory, checks the HTTP 503 response and automatic recovery readiness, then verifies streamed generation from the restored model. The real Qwen3.6 run passed after the loader reported `GGUF magic invalid`. The original engine's sealed accounting receipt was complete; the failed loader's crash receipt was explicitly degraded with unknown token totals. Cleanup and restoration of the protected llama.cpp workload passed.

The harness accepts separate `--source` and `--daemon-source` paths so the AMD runtime and the swap feature branch can be tested together without modifying a live checkout. `--extensions-dir` must identify a private cache prebuilt from the selected runtime source. Required arguments also include `--python`, `--model`, `--protected-service`, `--protected-url`, `--artifacts`, and `--allow-maintenance`. The fixture never replaces an existing model. Raw logs and result files contain private deployment details and must not be published unreviewed.

## Provenance and scope

The design was informed by [mostlygeek/llama-swap](https://github.com/mostlygeek/llama-swap), checked out locally at `41ec321b6216d838488b2a7d936274ed227c0c5e` on 2026-09-10. llama-swap is MIT licensed (`LICENSE.md`). No llama-swap or llama.cpp code is vendored, modified, or submitted by this feature. FreeToken remains the sole change and pull-request target.
