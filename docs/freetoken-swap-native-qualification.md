# Native freetoken-swap qualification runbook

This runbook qualifies the FreeToken-owned router. It does not qualify the
separate llama-swap integration and it does not authorize production activation
or a merge. Use only an approved maintenance window on **GMKtek EVO-X2**.

## Preconditions

- An approved authentication method for the qualification host is available.
- The protected workload, its exact restoration procedure, and a deterministic
  health request are recorded privately before any change.
- The current FreeToken feature branch is checked out in an isolated path.
- Model artifacts, tokenizer, native extension, and FreeToken runtime are
  verified known-good for one short deterministic completion before swap tests.
- The native catalog has two aliases with distinct model paths, loopback ports,
  bounded context settings, and no unreviewed `drop_fields` policy.
- `git status --short` is clean except for intentional qualification-only files.

Do not copy private paths, addresses, hardware identifiers, prompts, raw model
output, API keys, or request headers into the public PR.

## Baseline capture

Capture privately, before starting the daemon:

1. Protected workload health and one deterministic completion.
2. Current listener and process inventory for the selected temporary ports.
3. Host memory, accelerator-visible memory, and available system memory as
   separate values.
4. FreeToken branch commit, catalog hash, model file hashes, Python version,
   ROCm version, and runtime package versions.

Abort before loading if the protected workload is unhealthy or the measured
capacity is lower than the documented gate.

## Native router matrix

Run each test through the daemon's stable URL, never by calling the engine port
directly. Keep request and response content private. Record status codes,
model alias, elapsed time, first-byte time, final duration, usage-derived completion tokens/second, router metrics, engine metrics, accounting receipt IDs, and cleanup result.

| Test | Required observation | Pass condition |
| --- | --- | --- |
| Cold A | First request to alias A | Ready engine, valid ordinary completion, router activation increments |
| Warm A | Repeat alias A | Same engine PID, no activation increment, completion succeeds |
| Warm selector | Request the temporary warm selector while A is resident | Request is rewritten to A, completion succeeds, and activation remains unchanged |
| Runtime profile | Activate the temporary profile, request its pin through the warm selector, then clear it | Virtual pin is listed only while active, disabled pin stays omitted, completion uses resident A with zero activation, and the profile is cleared before later trials |
| Configured readiness target | Start and recheck temporary profiles through their configured `/ready` path | Control inventory reports `/ready`; activation and stable daemon readiness succeed without leaving the exact manager-owned port |
| Cold B | Request alias B after A is idle | A receives durable stop receipt, B becomes ready, completion succeeds |
| A to B to A | Three routed requests | Each expected alias returns, no overlapping owned children, every replacement is ready |
| SSE | Stream an alias request | First event and terminal event arrive, final lease count is zero |
| Explicit cancel | Send a long stream with `X-FT-Request-ID`, call router cancel | Same engine reaches zero active leases, cancellation counter increments, no normal completion is credited |
| Same-model concurrency | Two A requests | Both complete, one resident engine, no unintended switch |
| Conflicting request | Keep A stream active then request B | B waits or receives documented capacity response, A is not killed mid-stream |
| TTL | Allow a nonpersistent idle profile to reach its TTL | Engine stops through accounting path, listener closes, eviction increments |
| Bad replacement | Select an intentionally invalid disposable fixture | HTTP failure is visible, previous engine recovery is attempted only when applicable, failed receipt is degraded rather than fabricated |
| Reload | Replace catalog with a valid idle change, then an invalid or active-profile redefinition | Valid change applies atomically; invalid and active redefinitions are refused without altering live ownership |
| Authentication and control plane | Probe inference, both public model-list paths, namespaced direct upstream, and management without credentials, then exercise Bearer, Basic-password, and `X-Api-Key` before inspecting aliases, profiles, metrics, and router-log SSE | Unauthenticated inference, `/v1/models`, `/models`, and management return 401; both listings are equivalent apart from request timestamps; the temporary `compat/model-a` alias reaches resident A's `/v1/stats`; all three key forms expose exact resident A; authenticated inventory is consistent; metrics and a bounded `management_loaded` event are available |

## Separate performance evidence

`benchmarks/swap/qualify_native_router.py` is the opt-in Linux harness for
collecting the four required comparisons in one approved maintenance window.
It starts a private native daemon with a private state directory and extension
cache and a validated dynamic-port TOML catalog. It generates a fresh private
router API key for the run and scopes that credential to the exact temporary
daemon origin; the protected service and direct engine comparison never receive
it. Before performance trials, it requires unauthenticated `/router/status` and
`/v1/models` and `/models` requests to return 401, verifies their normalized
listing equivalence plus Bearer, Basic-password, and `X-Api-Key`, then
authenticates alias, selector, model, profile, configured readiness target,
Prometheus, and bounded router-log SSE checks. Their raw responses and the key-bearing
catalog remain private. The harness then records private raw artifacts for: a direct request to the
router-owned engine port, warm-selector and runtime-profile composition canaries, a warm routed request, a cold routed swap to the
other model, and an alternating routed swap back. It requires streamed OpenAI usage,
then records first-byte time, final duration, completion tokens, and usage-derived
decode tokens/second at the client. Before the comparison sequence it also opens a
long routed stream, explicitly cancels its opaque request ID, and fails unless the
router returns to idle, increments cancellation telemetry, emits no normal terminal
completion credit, and the retained private partial SSE lacks `[DONE]`. It then runs
two simultaneous same-alias streams and fails unless both complete with zero
activation delta and one unchanged resident profile. It stores the corresponding
`/router/status` snapshot and Prometheus `/metrics` response for each routed
comparison, and fails if activation counters do not prove the advertised
warm/cold/alternating state. It then switches to a deliberately missing private
model fixture and requires HTTP 503, a successful rollback launch, restored exact
identity, an activation-failure increment, and a valid completion from the restored
model. The harness compares the private accounting outbox before and after that
failure and requires at least one new valid receipt ID, publishing only the count.
It also writes a private active-profile priority change and requires the router to
reject it with HTTP 409 while retaining exact active identity.
Before that reload check, the harness gracefully terminates the first daemon while
leaving its test-owned engine detached, starts a replacement daemon against the same
private state, and requires the manager's adopted flag, engine PID, engine port, and
router profile identity to match. A routed completion must succeed with zero router
activations before the replacement daemon becomes the final cleanup owner.
It then holds a long model-A stream while requesting model B, requires B to be
visibly queued with A still exact and active, cancels A, and requires exactly one
activation into B followed by one activation restoring A. The cancelled A prefix
must not contain a normal terminal marker.
The harness then reloads a singleton persistent group while no model is resident,
loads that profile, and requires a conflicting load to return HTTP 409 while the
same PID remains exact and persistent. Explicit unload must release the slot and
allow the conflicting profile to activate.
Finally, it explicitly unloads its temporary resident, atomically reloads the private
catalog with a two-second idle TTL, verifies TTL-driven eviction and listener closure,
and leaves no temporary engine for daemon cleanup.
The direct comparison retains its router-owned load receipt and activation
snapshot privately as well.
It also saves the authenticated-local `/router/hardware` process and memory
snapshot for every comparison privately. Each loaded-model snapshot must contain
positive Linux process-tree PSS and per-process GPU-memory values with explicit
available/source markers; an unavailable probe or compatibility zero fails the
run. The published result must remain a sanitized aggregate.

The harness requires `--allow-maintenance`, the exact operating-system hostname
in `--expected-hostname`, a new empty `--artifacts` directory, two known-good
model paths, and the protected service's private restore endpoint. A hostname
mismatch fails before artifact creation, service inspection, or maintenance and
does not disclose either hostname. It then verifies the protected baseline, prebuilds kernels,
stops the protected service only after the native daemon is reachable, and
always attempts daemon cleanup and protected-workload restoration. Do not run
it on Windows or substitute a direct engine URL for the routed cases. Publish
only sanitized aggregate timings and explicit pass/fail results; raw responses,
paths, daemon logs, catalog, and host data remain private.
The harness also requires the final temporary engine listener to be closed
before it can report success.

## Restoration and acceptance

After testing:

1. Stop temporary daemon and all test engines through their owned lifecycle.
2. Verify temporary listeners are closed and no test worker process remains.
3. Restore the protected workload exactly as captured.
4. Verify its health and deterministic completion.
5. Preserve raw logs and request content privately. Publish only sanitized
   aggregate timings, pass or fail outcomes, anonymous hardware label, commit
   hashes, and explicit limitations.

The native route is not qualified by an open port, a green `/health`, or a
single start. Qualification requires the relevant end-to-end matrix evidence
above and protected-workload restoration.

