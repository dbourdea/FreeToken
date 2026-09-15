# freetoken-swap pinned-source inventory

This document decomposes the parity contract in
[`freetoken-swap-parity-matrix.md`](freetoken-swap-parity-matrix.md). The source
of truth is the read-only `mostlygeek/llama-swap` commit
`41ec321b6216d838488b2a7d936274ed227c0c5e`. Source was inspected with
`git show` and `git ls-tree`; no reference code is vendored. The pinned
`LICENSE.md` is the MIT License, copyright 2024 Benson Wong.

Classifications describe behavior, not matching names:

- **Native** — implemented in FreeToken and covered by deterministic tests.
- **Equivalent** — a different native contract provides the applicable
  behavior and is covered by deterministic tests.
- **Missing** — applicable behavior that is not implemented yet. A missing
  live-only proof is called out separately from missing implementation.
- **Deferred** — potentially applicable expansion that is not part of the
  current one-engine product contract. It remains an open difference, not
  parity.
- **Inapplicable** — impossible or misleading under a stated FreeToken backend
  or one-engine architectural constraint. A future capability change reopens
  the item.

The current-engine and GMKtek EVO-X2 maintenance qualification remains pending;
therefore **Native** never implies that the live gate is complete.

## Configuration schema

### Global fields

Pinned sources: `internal/config/config.go` (`Config`, `GroupConfig`,
`HookOnStartup`, `ProfileConfig`, `RoutingConfig`),
`internal/config/performance.go`, `internal/config/upstream.go`,
`internal/config/peer.go`, and `internal/config/tailcat.go`.

| Pinned field or block | Classification | FreeToken behavior and evidence location |
| --- | --- | --- |
| `models`, `apiKeys`, `globalTTL`, `unloadTimeout`, `globalConcurrencyLimit`, `includeAliasesInList`, `sendLoadingState` | **Native** | Allowlisted TOML equivalents in `python/freetoken/daemon/catalog.py`; routing/auth/list/loading tests in `tests/daemon/test_catalog.py` and `test_router.py`. |
| `startPort` | **Equivalent** | Each profile accepts an explicit port; `port = 0` asks the kernel for a loopback port at activation. Allocation and reactivation are tested. |
| `routing.scheduler.use=fifo` and FIFO priorities | **Native** | One priority-aware FIFO coordinator in `python/freetoken/daemon/router.py`; unsupported schedulers fail validation. |
| group `members`, `swap`, `exclusive`, `persistent` | **Native applicable subset** | Membership and persistent protection are native. Configuration that requests coexistence outside the sole resident slot is rejected rather than weakened. |
| matrix `vars`, `sets`, `evict_costs` | **Inapplicable today** | `ServeManager` owns exactly one child, so there is no co-resident set or victim choice to solve. This reopens if FreeToken gains multi-engine ownership. |
| startup `hooks.on_startup.preload` and `profile` | **Native applicable subset** | `router.preload_model` allows one concrete model/alias and `router.startup_routing_profile` selects a validated pin map. Multiple preloads/selectors are rejected under one-resident capacity. |
| runtime `profiles` descriptions and pin maps, including disabled pins | **Native** | `[profiles.<name>.pins]` and authenticated activation API; parser, routing, reload, and lifespan tests. |
| `selectors` (`pin`, `warm`, `spillover`) | **Native applicable subset** | `pin` and `warm` are native. `spillover` is **inapplicable today** because it requires simultaneous reservations across local residents or peers. |
| global `macros` | **Inapplicable by safety contract** | FreeToken accepts argument vectors and explicit typed fields; arbitrary command/proxy/environment interpolation is rejected to prevent shell and target injection. |
| `peers` and peer credentials/filters/timeouts | **Deferred** | The current contract is one local FreeToken-owned engine. No distributed peer transport is claimed. |
| `upstream.ignorePaths` | **Native safe subset** | `router.upstream_no_activation_suffixes` defaults to the pinned static extensions, returns 409 before reservation/activation/upstream I/O while the exact local model is unloaded, and proxies normally when resident. A bounded validated suffix list replaces arbitrary regex to avoid a regex execution surface. |
| `healthCheckTimeout` | **Native** | Per-profile `ready_timeout_s` bounds readiness; the checked path is configurable. |
| request-log level/time/stdio fields | **Equivalent** | Native daemon logging and bounded rings have their own process-level controls; these are not hot catalog policy. Router events deliberately omit bodies, headers, query strings, and secrets. |
| `metricsMaxInMemory` | **Equivalent** | Native router logs and metric state are bounded; Prometheus counters are aggregate rather than a queryable in-memory activity table. |
| `captureBuffer` | **Native safe equivalent** | `router.capture_buffer_mb` is opt-in and defaults to zero. Captures are credential-redacted, serialized-byte-budgeted, per-response capped, binary-safe, memory-only, and retrieved by activity ID. |
| `store.path` | **Native safe equivalent** | The daemon-owned state directory contains lifecycle/accounting state and bounded body-free `activity.jsonl`. Rows are fsynced, streamed on recovery, strictly validated, and atomically compacted; persistence health is exposed without its path. Captures remain memory-only. |
| `ui.activity.session_id` | **Native privacy-preserving equivalent** | Validated non-credential header names select the first nonempty value, but only a stable truncated SHA-256 label is stored and shown. Matching is case-insensitive and raw identifiers/general headers are not persisted. |
| `performance.disabled`, `performance.every` | **Native privacy-preserving equivalent** | Validated `router.performance_disabled` and `performance_every_s` (5–3600 seconds) control an app-owned sampler retaining at most one hour in memory. It samples only the owned engine process-tree RAM/VRAM probe. |
| `tailcat` | **Deferred** | No Tailcat network dependency or remote-listener product contract exists. Local auth and route allowlisting do not claim Tailcat interoperability. |

### Per-model fields

Pinned source: `internal/config/model_config.go` (`ModelConfig`,
`TimeoutsConfig`, `CompatConfig`, `ModelCapConfig`) and
`internal/config/filters.go` (`Filters`).

| Pinned field | Classification | FreeToken behavior and evidence location |
| --- | --- | --- |
| `cmd` | **Equivalent, safer** | `model` plus `args` constructs an allowlisted `ft serve` argument vector without a shell. Unknown daemon-owned options are rejected. |
| `cmdStop` | **Inapplicable by ownership contract** | `ServeManager` performs drain/abort, exact-identity signalling, process-group cleanup, accounting, and rollback; arbitrary stop commands would create a second lifecycle authority. |
| `env` | **Inapplicable by safety contract** | Per-profile environment injection is rejected. The daemon inherits its controlled service environment. |
| `proxy`, `checkEndpoint` | **Native applicable subset** | Exact plain-HTTP loopback `${PORT}` target with optional fixed path prefix and a safe readiness path. Remote targets, credentials, fragments, traversal, and ambiguous port templates fail closed. |
| `aliases`, `unlisted`, `useModelName` | **Native** | Collision-safe canonicalization/listing and outbound JSON model rewrite with client routing identity retained. |
| `ttl`, `unloadTimeout` | **Native** | Per-profile override plus global default, idle-only eviction, and manager-owned graceful stop. |
| `name`, `description`, `metadata` | **Native** | JSON-compatible metadata with router-owned identity/capability precedence; no local model paths or args leak through public listings. |
| `concurrencyLimit` | **Native** | Canonical and alternate IDs share one reservation cap; admission rejects before lifecycle/upstream work. |
| `filters.stripParams`, `setParams`, `setParamsByID` | **Native** | `drop_fields`, hard/soft `set_fields`, and `set_fields_by_id` preserve the pinned strip/global/by-ID order and protect `model`. Nested safe JSON paths extend the flat pinned behavior. |
| per-model `macros` | **Inapplicable by safety contract** | Explicit typed fields replace arbitrary interpolation. |
| `sendLoadingState` | **Native** | Nullable per-profile override of the global setting for admitted cold streaming chat requests. |
| timeout `connect`, `responseHeader` | **Equivalent** | One per-profile/global upstream socket deadline bounds connect and response reads for ordinary and SSE requests. It is deliberately simpler than independent phase timers. |
| timeout `keepalive`, `idleConn` | **Inapplicable today** | Native proxy calls use fresh manager-owned loopback HTTP connections, not a reusable idle pool. |
| timeout `tlsHandshake` | **Inapplicable today** | Valid proxy targets are plain HTTP loopback only. |
| timeout `expectContinue` | **Inapplicable today** | The supported small JSON text routes are forwarded over a fresh local connection without an Expect/Continue policy surface. |
| `compat.ignoreWebsockets` | **Inapplicable today** | Neither the current FreeToken engine nor the stable router registers a websocket inference route. |
| capabilities `in`, `out`, `tools`, `context` | **Native declarative subset** | Text/tool/context listing metadata is native and does not enable inference features. Unsupported image/audio/video declarations fail closed. |
| capability `reranker` | **Inapplicable today** | FreeToken has no rerank backend route, so advertising it is rejected. |
| copied `healthCheckTimeout` | **Native** | Resolved directly from each profile's `ready_timeout_s`. |

## HTTP and management routes

Pinned route source: `internal/server/server.go` (`modelPostJSONRoutes`,
`modelPostFormRoutes`, `modelGetRoutes`, `routes`, `ServeTailcatHTTP`). Native
registrations are in `python/freetoken/daemon/app.py`.

| Pinned route family | Classification | Native behavior or boundary |
| --- | --- | --- |
| `POST /v1/chat/completions`, `/v1/completions`, `/v1/responses`, `/v1/messages`, `/v1/messages/count_tokens` | **Native** | Automatic model-ID inference, lifecycle acquisition, filtering, byte/SSE forwarding, cancellation and accounting share one coordinator. |
| `/v/*` versionless aliases, `/completion`, `/infill` | **Inapplicable today** | The current engine does not register these model-bearing aliases. Explicit profile-qualified upstream access remains available. |
| embeddings and rerank/reranking families | **Inapplicable today** | No matching FreeToken backend modality/route. |
| audio speech/voices/transcriptions and generic audio task route | **Inapplicable today** | No matching FreeToken backend modality/route. |
| image generations/edits, SDAPI, `/props`, ComfyUI | **Inapplicable today** | No matching FreeToken backend modality/route. |
| `GET /v1/models`, `/models` | **Native** | Authenticated canonical/optional-alias listing with atomic loaded state, display metadata and CORS. |
| `/logs` and `/logs/stream*` | **Equivalent** | Bounded engine and router streams use `/engine/logs` and `/router/logs?since=` with replay/resume behavior. |
| `/health`, `/wol-health` | **Native / inapplicable split** | `/health` is native liveness; `/ready` is stricter readiness. Wake-on-LAN health is not part of the local service contract. |
| root redirect, favicon, `/ui/` | **Equivalent** | Dependency-free local management UI is native; matching static asset names are not a parity requirement. |
| `/metrics` | **Native** | Authenticated Prometheus lifecycle, queue, cancellation, activation, timing, bytes and throughput signals. |
| `/unload`, `/running` | **Equivalent** | `/router/unload`, `/router/status`, and `/router/models`; one/all unload and configured/resident views are tested. |
| `/upstream/{model}/{path...}` | **Native** | Same admission/lifecycle lease, longest slash-namespaced ID, escaped suffix/query preservation, safe credential termination, and a pre-admission static-suffix guard that returns 409 rather than cold-loading. |
| `/api/models/unload*`, `/api/profiles`, `/api/profiles/active` | **Equivalent** | Native router management APIs implement the behavior under one-resident capacity. |
| `/api/inflight/{id}/cancel` | **Equivalent** | Opaque request reservation/list/cancel API covers queued, connecting, and active requests. |
| `/api/events` | **Equivalent** | Bounded resumable router event stream; route templates and lifecycle facts only. |
| `/api/metrics/activity`, `/api/metrics/stats` | **Native bounded equivalent** | Authenticated `/router/activity` supports newest-first bounded pagination and model filtering; `/router/activity/stats` reports counts, errors, cancellation, bytes, and average duration. Rows are body-free. |
| `/api/performance` | **Native privacy-preserving equivalent** | Authenticated pinned and native route aliases return a bounded one-hour `sys_stats` history with strict RFC3339 `after` filtering. Rows declare engine-process-tree scope and RAM/VRAM availability/source; `gpu_stats` stays empty rather than fabricating adapter-wide sensors. Disabled monitoring returns the pinned 503 `{enabled:false}` contract. |
| `/api/version` | **Equivalent** | `ft --version` and package version provide build identity; no duplicate router JSON endpoint is required for lifecycle behavior. |
| `/api/hardware` | **Native** | `/router/hardware` reports process-tree RAM and explicit available/source GPU memory. |
| `/api/captures/{id}` | **Native safe equivalent** | Authenticated opt-in retrieval by activity ID with pinned and custom credential-header redaction, Base64 bodies, one-MiB response cap, total serialized-byte budget, and no capture for cancellation/overflow. |
| `/api/mcp` | **Deferred** | The pinned endpoint exposes llama-swap's embedded docs/tools. FreeToken has no equivalent agent-tool product contract. |
| `/api/tailcat` and Tailcat listener restrictions | **Deferred** | No Tailcat listener or client protocol is claimed. |

## Lifecycle and routing internals

| Pinned source subsystem | Classification | FreeToken implementation |
| --- | --- | --- |
| `internal/router/{base,router,loading}.go` | **Native** | `RoutingCoordinator` owns admission, loading feedback, leases, readiness, eviction and routing snapshots. |
| `internal/router/group.go` and FIFO scheduler | **Native applicable subset** | Exclusive one-slot routing, persistent protection, priority and FIFO are deterministic-tested. |
| `internal/router/{matrix,matrix_solver}.go` | **Inapplicable today** | No multi-resident placement or victim set exists under one child. |
| `internal/router/peer.go` | **Deferred** | No remote peer transport in the local one-engine contract. |
| `internal/process/*` | **Native** | `ServeManager`, `osproc.py`, `pidfile.py`, and accounting state provide launch, exact identity, stop/reap/tree cleanup, rollback and re-adoption. |
| server profile/selector/filter middleware | **Native** | Order is routing profile, selector, alias, target filtering, admission and proxy; queued requests retain their admitted policy snapshot. |
| global and model concurrency middleware | **Native** | Reservations include queued/activating/active work and release once on every terminal path. |

## Authentication, observability, UI, and persistence

| Pinned behavior | Classification | FreeToken implementation or gap |
| --- | --- | --- |
| API-key middleware | **Native** | Case-insensitive Bearer, Basic password, and `X-Api-Key`; dedicated `X-FT-Token` control override; upstream credential stripping and rotation tests. |
| Inflight ownership/cancellation | **Native** | Opaque IDs reserve before admission and cancel queued, connecting, or active work. |
| Bounded logs and SSE resume | **Native** | Separate engine and privacy-safe router rings. |
| Prometheus metrics | **Native** | Lifecycle, queue, activation, cancellation, eviction, terminal stream, TTFT, duration and byte signals. |
| Bounded activity/performance stores | **Native** | Body-free inference activity survives restart in a bounded fsynced/compacted store. Performance history is intentionally memory-only and retains at most one hour, matching the pinned ring behavior. |
| Redacted bounded request/response captures | **Native** | Disabled by default; opt-in memory budget, sensitive-header redaction, binary-safe bodies, overflow/cancellation refusal, authenticated retrieval, and deterministic tests. Captures must never become public evidence artifacts. |
| Embedded management UI | **Native applicable subset** | Status/models/profiles/requests/logs/metrics/hardware/performance plus body-free activity and explicit-on-click capture views are local and dependency-free. The initial HTML embeds no operational data. |
| Hardware snapshot | **Native, extended** | Current process-tree RAM plus NVIDIA/AMD per-process VRAM, with unavailable distinct from zero. |
| Embedded documentation MCP | **Deferred** | No FreeToken MCP contract. This does not affect inference or lifecycle parity. |
| Tailcat remote access | **Deferred** | No FreeToken Tailcat contract. This does not imply generic remote access is safe. |

## Tests and evidence classes

Pinned source tests span `internal/**/*_test.go`, router/process/config/server
tests, and UI tests. Native deterministic coverage lives in `tests/daemon`:

| Evidence class | Current state |
| --- | --- |
| Catalog validation, routing, HTTP/auth/SSE, filters, profiles/selectors, loading state, cancellation, TTL, reload, metrics/logs, process/accounting and startup hooks | **Native deterministic evidence present.** |
| Disposable actual-child process, process-group cleanup, re-adoption and routed SSE on Linux | **Native hosted-Linux evidence present** at the exact PR lineage recorded in the parity matrix. |
| Combined-tree/current engine compatibility | A clean synthetic tree at the recorded current swap/AMD heads passed 377 daemon/privacy/benchmark/reproducibility tests (7 Windows skips) and 21 model tests. Current-engine and protected restoration evidence remain required. |
| GMKtek EVO-X2 direct/warm/cold/A-B-A/concurrency/cancellation/failure/rollback/re-adoption/reload/TTL/auth/metrics/logs/restoration | **Live evidence missing; maintenance authorization required.** |
| Bounded activity/stat and opt-in capture APIs | **Native deterministic implementation and tests present.** Body-free rows survive app reconstruction; captures remain memory-only by policy. UI fetches captures only on explicit selection. |
| Periodic performance history | **Native deterministic implementation and tests present.** One-hour eviction, filtering, privacy, auth, disabled behavior, probe failure isolation, and sampler generation cleanup are covered. |

## Open applicable implementation gaps

No protocol-agnostic implementation gap is currently identified by this pinned
source inventory. Pending current-engine, GPU-model, combined-tree, and protected
restoration qualification remains an evidence gap and must not be conflated with
implementation parity.
