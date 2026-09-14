# freetoken-swap parity matrix

This is the implementation acceptance contract for native `freetoken-swap`.
It is based on the read-only official llama-swap reference at commit
`41ec321b6216d838488b2a7d936274ed227c0c5e`, MIT licensed. It does not copy
that project's code or authorize changes outside FreeToken.

Status labels:

- **Native**: implemented by FreeToken and behaviorally tested.
- **Integrated only**: available only when an unmodified llama-swap binary
  supervises FreeToken. This is not native parity.
- **Missing**: applicable, not yet implemented.
- **Inapplicable**: the current FreeToken server lacks the corresponding
  backend modality. The absent route is named explicitly rather than claimed.

## Pinned-source inventory

The following is a read-only source inventory, obtained with `git show` and
`git ls-tree` from the pinned commit rather than from the damaged local working
copy. It makes the scope of the comparison auditable without vendoring any
llama-swap code.

| Reference source at `41ec321…` | Observed responsibility | Native classification and evidence |
| --- | --- | --- |
| `internal/server/server.go` (`modelPostJSONRoutes`, `modelPostFormRoutes`, `modelGetRoutes`, `routes`) | Model-dispatched OpenAI, Anthropic, embeddings, rerank, audio, images, SDAPI, ComfyUI and upstream routes; list, health, unload, running, logs, metrics, UI, API group | Native text-generation routes, guarded passthrough, and a local management UI are implemented and HTTP-tested. Embedding, rerank, image, speech, transcription, SDAPI and ComfyUI are **inapplicable** because FreeToken exposes no matching backend route. MCP and Tailcat remain explicitly deferred product surfaces. |
| `internal/config/{config,model_config,commands,filters,macros,selectors,profile,upstream,performance,peer,tailcat}.go` | YAML schema, command/macro expansion, request rewriting, profiles, peers, hardware/performance policy | Native allowlisted TOML parser rejects commands/macros and unsafe owned options; aliases, dynamic ports, readiness, TTL, groups, priorities, keys, upstream timeout, safe filters and atomic reload are behavior-tested. Arbitrary transforms, macros, peer and Tailcat policy are deferred rather than emulated unsafely. |
| `internal/router/{router,base,loading,group,matrix,matrix_solver,peer}.go`, `internal/router/scheduler/fifo.go` | Loading, queueing, group/matrix and peer routing | Native single-owner FIFO/priority coordinator, exclusive one-resident capacity, persistent-group protection, leases, eviction and cancellation are tested. Multi-resident matrix solving and peers are deferred: the declared one-engine supervisor cannot prove safe concurrent residency. |
| `internal/process/{process,process_command,runtime_*,treecleanup_*}.go` | Child launch, process identity, stop/reap/tree cleanup | Native `ServeManager` owns the child, durable state, exact identity/re-adoption, process-group cleanup, drain/abort accounting and rollback. On daemon reconstruction, the routing coordinator now binds one unambiguous catalog profile to an exact fixed- or dynamic-port adopted identity; ambiguous or argument-mismatched identities fail closed. Deterministic and Linux actual-child recovery tests cover this boundary. |
| `internal/server/{auth,profiles,inflight,log,metrics,metrics_middleware,api,apigroup}.go`, `internal/logmon/*`, `internal/perf/*`, `internal/store/*` | API-key auth, profiles, inflight cancellation, log streams, Prometheus/activity/performance and persistence | Native bearer/control authentication, profiles, opaque cancellation, bounded engine/router logs, Prometheus lifecycle/queue/transport signals and durable accounting are implemented. Token throughput, memory and extended performance evidence remain bounded live-test gates. |
| `internal/server/{ui,apimcp,captures,tailcat}.go`, `ui/*`, `internal/mcptools/*`, `internal/tailcat/*` | Browser UI, embedded MCP, captures and Tailcat | Native local management UI is implemented; MCP, captures and Tailcat are **deferred**, not silently compatible, because FreeToken has no corresponding product contract. |
| `internal/**/*_test.go`, `docs/kb/guides/**/*` | Reference behavioral tests and operator documentation | Native tests live in `tests/daemon`; the qualification runbook and completion audit separate deterministic, Linux and approved maintenance-window evidence. |

| Pinned llama-swap capability | Current FreeToken state | Required native parity evidence |
| --- | --- | --- |
| Model catalog and aliases | Native TOML catalog with validated model, port, args, readiness, unload, and upstream response timeouts. `port = 0` requests a concrete kernel-selected loopback port for each activation. | Deterministic tests cover dynamic-port residency stability and a fresh target after a swap; a Linux real-child test exercises fresh dynamic ports across eviction/reactivation. Native selector transforms remain intentionally unsupported except safe `drop_fields`. |
| Start, stop, switch, PID identity, re-adoption | Native and tested | Preserve as router substrate; exercise automatic-request ownership |
| Readiness and diagnostic health | Native `/ready` plus diagnostic `/health` | Preserve exact HTTP behavior through the unified router |
| Automatic OpenAI model-ID routing | Native single-engine coordinator with priority-aware admission and health-gated activation | `tests/daemon/test_router.py` covers cold activation, same-model concurrent leases, safe swap waiting, and unknown-model errors. Linux and GMKtek EVO-X2 evidence remains required. |
| OpenAI model list, completion and chat completion forwarding | Native authenticated `GET /v1/models` exposes only configured aliases; request-byte-preserving proxy includes SSE body forwarding | Deterministic tests cover aliases without local model-path disclosure, every supported text endpoint, request bytes, SSE bytes, upstream error status/body/safe headers, and lease release. Direct, cold, warm, cancellation, and performance evidence remains required. |
| OpenAI Responses endpoint | Native `POST /v1/responses` uses the same admission and proxy contract. FreeToken's stateless response lookup/cancel stubs return 404 by design, so they have no model lifecycle to route. | Add explicit routed response-object and cancellation proof for any future stateful backend. |
| Anthropic Messages and token-count routing | Native routes use the same admission and proxy contract | Deterministic HTTP tests cover both Messages and token-count routing; add live failure proof. |
| FreeToken legacy `POST /generate` | The request schema has no model identifier, so an automatic route at the stable daemon URL is intentionally inapplicable: choosing a model would require an unsafe implicit default. Profile-qualified `POST /upstream/{profile}/generate` remains available through unified admission. | Deterministic HTTP proof rejects ambiguous top-level `/generate` and preserves the explicit passthrough method, body, SSE response, and lease. |
| Unknown-model status and direct upstream access | Native stable `unknown_model` error envelope and `/upstream/{profile}/...` passthrough through the same lease | Deterministic HTTP tests prove the identical 404 error type across all five routed text endpoints, plus GET passthrough, query forwarding, and rejection of unsafe direct `prepare-stop`; add real-engine passthrough coverage. |
| FIFO, priority, exclusive group routing | Native priority-aware FIFO queue and one-engine exclusive admission. The TOML parser rejects coexistence flags it cannot honor, while admitting singleton persistent protected slots. | Deterministic tests cover priority-before-earlier-low-priority queueing, accepted/rejected group policy and capacity protection. The private native harness holds A, proves B queues without disturbing A, cancels A, and requires ordered B then A activation; current GMKtek execution remains required. |
| Matrix or equivalent capacity policy and eviction costs | **Native equivalent policy:** the sole `ServeManager` child is the one resident slot; status exposes its exact identity, group, availability, queue, and eviction decisions. | Deterministic tests and the private maintenance harness cover exclusive transitions and persistent-slot protection. Multi-resident matrix solving and memory-ranked victim selection are **inapplicable under one-engine ownership** because there is never a choice among co-resident victims; they become deferred requirements only if FreeToken adds multi-engine ownership. |
| Persistent resident models | Native persistent group protects the sole resident slot until explicit unload | Deterministic capacity-protection test exists. Multi-resident preload is unavailable with the current one-engine supervisor. |
| TTL and unload timeout | Native timer schedules idle-only eviction; authenticated `POST /router/unload` uses the profile or global graceful-stop timeout and the existing accounting transaction | Deterministic lease/TTL and explicit-unload tests cover no eviction while leased, profile timeout selection, and durable manager cleanup; real-engine endurance remains separately bounded. |
| Load/unload management API and running-model list | Native router status, configured plus resident `/router/models`, `POST /router/load`, and `POST /router/unload` through the same lifecycle coordinator. A named body unloads that profile; no body unloads all residents (the current resident under one-engine capacity). | Deterministic HTTP tests prove named mismatch preservation, named unload, and no-body unload-all. Load-all and multi-resident management are inapplicable to the explicit one-engine capacity policy. |
| Profiles | **Native:** `/router/profiles`, validated aliases, per-profile lifecycle settings, arguments, priority, group membership, and safe `drop_fields`, with activation through routed requests or explicit controls | Arbitrary selector expressions and profile transforms are intentionally deferred because FreeToken has no corresponding safe product contract; unsupported configuration is rejected rather than evaluated. |
| API keys | Native router bearer keys protect inference and, absent a separate daemon token, management; `X-FT-Token` remains the dedicated control-plane override | Deterministic authorization tests cover inference, router status, and atomic catalog-driven key rotation. |
| Logs and bounded streaming logs | Native, separate bounded router event ring at authenticated `GET /router/logs?since=` with the same replay/resume/SSE contract as engine logs | Deterministic tests prove admission/completion events, privacy-safe payloads, bounded ring behavior, and management authorization. |
| Prometheus and activity/performance metrics | Native `/metrics` exposes bounded router admission, queue wait, active-identity, activation time, failure, cancellation, eviction, normal-terminal-stream, last-TTFT, last-duration, response-byte, and proxy-byte-rate signals; router-cancelled streams are not credited as normal terminal completions; engine metrics remain separately available | `benchmarks/swap/qualify_native_router.py` collects private direct/warm/cold/alternating first-byte, duration, and streamed-usage-derived completion-token-rate evidence. It still requires an approved Linux GMKtek EVO-X2 execution, including model throughput, process, and memory observations. |
| Inflight cancellation API | Native router issues or accepts opaque `X-FT-Request-ID` values, atomically reserves them before admission, removes disconnected waiters from the admission queue, lists active IDs, and provides `POST /router/requests/{id}/cancel` | Deterministic tests prove duplicate IDs cannot create a second admission or upstream request; queued disconnect cannot trigger a later swap; failed, disconnected, or cancelled admission and failed connect release ownership; and active cancellation closes the socket, releases the lease, and increments its metric. Same-instance real-engine terminal-abort proof remains required. |
| Parameter filters and configuration hooks | Native profile `drop_fields` removes explicitly configured safe top-level JSON fields only; default forwarding preserves original bytes | Arbitrary set-parameter transforms and lifecycle shell hooks are intentionally unsupported for safety. |
| Configuration watch/reload | Native authenticated `POST /router/reload` and default cross-platform local catalog polling re-parse and atomically validate the catalog. Watch status and sanitized results are observable. | Deterministic tests cover manual valid replacement, invalid-file rejection, active-profile scheduling/effective-lifecycle redefinition refusal, watcher valid replacement and watcher rejection. Real-engine reload evidence remains required. |
| UI, hardware, captures, MCP, Tailcat | Native dependency-free `/ui/` management shell and authenticated `/router/hardware` memory view. Captures, MCP and Tailcat are out of FreeToken's current product scope. | Deterministic HTTP tests prove the UI embeds no configuration or secret values and hardware data remains API-key gated. |
| Embedding, rerank, image, speech, transcription, ComfyUI, SDAPI routes | Inapplicable today where FreeToken has no matching server route | Document absent FreeToken backend capability and reject safely. Do not mimic endpoint success |
| Accounting, drain/abort barrier, rollback | Native automatic routing delegates every stop/switch to `ServeManager`; readiness and launch failures retain its recovery result, including through `POST /router/load` | Deterministic routing and management-API tests prove recovery evidence and restored exact identity. The private native harness now requires a failed disposable real-model switch, rollback launch, new durable outbox receipt, failure-counter increment, and restored completion; current-branch Linux and GMKtek execution remain required. |

## Native real-process gate

`tests/daemon/test_real_process_recovery.py` now includes a Linux-only native
router test that starts a disposable HTTP child through `ServeManager`, waits
for real `/health` readiness, routes an SSE request through the daemon, then
stops the child and verifies pidfile cleanup. A second Linux-only test persists
a live disposable child as prior-daemon state, re-adopts it into a new manager,
binds the exact catalog profile in a new routing coordinator, routes SSE without
calling the spawn function, and verifies cleanup by the new owner. It compiles and is skipped on
Windows. It has not yet been executed on a Linux host, so it is a pending gate,
not evidence of Linux completion.

## Architecture gate

The target is one FreeToken-owned router and lifecycle supervisor. It must not
delegate automatic routing to llama-swap while retaining safety only in the
manual daemon. The existing llama-swap integration remains a compatibility and
comparison reference until native request routing reaches the acceptance gates.

## Remaining acceptance sequence

1. Execute the current Linux real-process tests, including dynamic-port cleanup,
   rollback, accounting, and router-bound re-adoption.
2. In an approved GMKtek EVO-X2 maintenance window, run the private native
   qualification harness through direct, warm, cold, alternating, cancellation,
   same-model concurrency, conflicting-model drain, failed-switch recovery,
   daemon re-adoption, reload-conflict, persistent-capacity, and TTL gates.
3. Restore and health-check the protected workload, retain raw evidence privately,
   and publish only sanitized aggregate observations in the final audit.
4. Re-run deterministic and combined-tree compatibility suites at the final PR
   head and keep the PR draft until all applicable evidence is linked.

Every row moves to Native only after deterministic tests and relevant live
evidence are linked here. No endpoint name alone establishes parity.

The privacy-safe native live acceptance matrix is maintained in
[native qualification runbook](freetoken-swap-native-qualification.md).
