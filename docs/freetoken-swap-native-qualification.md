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
model alias, elapsed time, first-byte time, final duration, router metrics,
engine metrics, accounting receipt IDs, and cleanup result.

| Test | Required observation | Pass condition |
| --- | --- | --- |
| Cold A | First request to alias A | Ready engine, valid ordinary completion, router activation increments |
| Warm A | Repeat alias A | Same engine PID, no activation increment, completion succeeds |
| Cold B | Request alias B after A is idle | A receives durable stop receipt, B becomes ready, completion succeeds |
| A to B to A | Three routed requests | Each expected alias returns, no overlapping owned children, every replacement is ready |
| SSE | Stream an alias request | First event and terminal event arrive, final lease count is zero |
| Explicit cancel | Send a long stream with `X-FT-Request-ID`, call router cancel | Same engine reaches zero active leases, cancellation counter increments, no normal completion is credited |
| Same-model concurrency | Two A requests | Both complete, one resident engine, no unintended switch |
| Conflicting request | Keep A stream active then request B | B waits or receives documented capacity response, A is not killed mid-stream |
| TTL | Allow a nonpersistent idle profile to reach its TTL | Engine stops through accounting path, listener closes, eviction increments |
| Bad replacement | Select an intentionally invalid disposable fixture | HTTP failure is visible, previous engine recovery is attempted only when applicable, failed receipt is degraded rather than fabricated |
| Reload | Replace catalog with a valid idle change, then an invalid or active-profile redefinition | Valid change applies atomically; invalid and active redefinitions are refused without altering live ownership |

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

