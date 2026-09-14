# FreeToken swap completion audit

This audit preserves the full integration goal. A draft PR and passing CPU tests
do not establish that every lifecycle behavior is qualified on real models. It
distinguishes historical evidence from current-branch evidence: neither is
silently promoted to proof for a later native-router implementation.

## Historical combined-source verification

- Swap source: `64dcc683d4e767fb4af8b7088ebb58564b1b7535`.
- AMD model-repair source: `de23ad6a9e74aecc72b9f6b9e81b8c3376ff2e60`.
- Git's clean merge-tree result: `c3c0ae54a09857b98bba83cfc75b91264e6eeb43`.
- The combined tree was archived into an isolated temporary directory on
  GMKtek EVO-X2. Neither branch nor the live runtime was replaced by that tree.
- Historical Linux validation: 114 daemon, privacy, benchmark, and reproducibility tests
  passed, including the real child-process recovery tests. No skips.
- Combined-tree Qwen validation: 21 grouped-output, SSM, and config tests passed.
- The protected llama.cpp service remained active throughout those CPU checks.
  This archived combined tree is not the current `freetoken-swap` branch.

Reproduce the combined-tree CPU suites from the extracted source, with its
`python` directory on `PYTHONPATH` and the required test dependencies installed:

```bash
python -m pytest tests/daemon \
  tests/benchmarks/test_public_document_privacy.py \
  tests/benchmarks/test_gmk_evo_x2_benchmark.py \
  tests/reproduce/test_collect_host_manifest.py -q
python -m pytest tests/models/test_qwen36_gdn_grouped_output.py \
  tests/models/test_qwen35_gguf_ssm_a.py \
  tests/models/test_qwen35_gguf_config.py -q
```

## Current checkout verification

- Read-only comparison reference: `mostlygeek/llama-swap`
  `41ec321b6216d838488b2a7d936274ed227c0c5e`, whose `LICENSE.md` says MIT.
- Local deterministic verification on the current Windows checkout: 179 daemon
  tests passed and 7 Linux-only tests were skipped. This proves CPU/HTTP
  behavior only; it does not substitute for Linux real-child or real-model
  evidence.
- No current-branch maintenance-window benchmark artifact has been published.
  Raw paths, prompts, responses, logs, and host data must remain private.

## Requirement evidence and gaps

| Requirement | Evidence | Status |
| --- | --- | --- |
| Official source, license, and provenance | Read-only llama-swap reference pinned to `41ec321b6216d838488b2a7d936274ed227c0c5e`, MIT license; research report and configuration example | Documented and reverified locally |
| Model catalog and lifecycle controls | Validated TOML catalog, collision-safe alternate IDs, unlisted profiles, authenticated profile endpoints, native process manager | Implemented and CPU/HTTP tested |
| Automatic model routing | Native `freetoken-swap` model-ID admission, readiness-gated activation, request-preserving proxying, cancellation, TTL eviction, reload, and deterministic HTTP tests; prior direct llama-swap runs remain comparison evidence only | Implemented and CPU/HTTP tested; current native real-engine qualification remains required |
| Readiness and API compatibility | Separate `/ready`, uncached generation-aware profile checks, ordinary and SSE completions, side-effect-free sanitized browser preflight and authenticated model-list CORS | CPU/HTTP tested; current native real-engine evidence required |
| Concurrency and unloading | Same-model and conflicting-model admission plus idle eviction are deterministically tested | Current native real-engine verification required |
| Rollback protections | Launch/readiness recovery, newer lifecycle intent, accounting preservation, and Linux real-child tests are implemented; historical invalid-GGUF evidence is retained separately | Current Linux/current-branch recovery execution required |
| Client cancellation | Native opaque router request IDs, atomic duplicate-ID rejection before admission/upstream work, disconnect-aware admission, queued/connecting/active request list, explicit cancel endpoint across every owned phase, orphan socket close, lease release, and cancellation metrics. Failed, disconnected, or cancelled admission and failed upstream connection release ownership safely. | Deterministic HTTP tested; current native same-instance GPU verification required |
| Authentication and observability | Bearer-protected inference/management, configured aliases and profiles, Prometheus metrics, bounded router-log SSE, and exact-origin qualification credentials | Deterministic HTTP tested; current native GMKtek control-plane execution required |
| Model compatibility | Mixed-format Qwen/GDN repair, tokenizer checks, exact-model contracts, prior live completion evidence, 21 combined-tree model tests | Qualified only for documented models and bounded workloads |
| Production protection | Isolated test paths, explicit maintenance gate, historical restore/completion checks, no interruption during combined-tree checks | Maintained; no current protected workload was touched |
| Privacy | Generic GMKtek EVO-X2 label, sanitized public metadata and examples, privacy regressions, regenerated reviewed PDF | Current publication changes sanitized; historical copies not erased |
| FreeToken-only publication | Anonymous GitHub API recheck on 2026-09-14: draft PR 1 is open from `feat/freetoken-swap` to `main` and reports `mergeable_state=clean`; draft PR 2 remains open on its separate AMD branch and also reports clean | Submitted, draft, not merged |

The PRs target different base branches: PR 1 targets `main`; PR 2 targets
`amd-rocm-gfx1151`. Their current open/draft/clean state was rechecked through
anonymous public metadata; no authenticated mutation was attempted. The clean combined tree is compatibility evidence, not an
instruction to merge either PR or change the repository's release strategy.
GitHub reported no status checks for either PR at this audit. The test results
above are independently executed evidence, not claims of passing hosted CI.

## Historical maintenance-window evidence

The following records describe an earlier approved window, not current-branch
completion proof:

1. GPU stream cancellation reached terminal idle on the same backend, without
   a normal-completion increment. Post-disconnect A-to-B-to-A streaming,
   concurrency, and TTL unloading passed.
2. Native daemon recovery passed after the real loader rejected an invalid
   GGUF fixture. The restored Qwen3.6 model reached readiness and generated the
   expected answer. The failed switch correctly remained HTTP 503.
3. Both phases restored and health-checked the protected service, including a
   verified completion. Final process/listener checks found no test runtime
   remaining. The accounting gap for the crashed loader is explicitly degraded.

The approved historical window is closed. No permanent production activation,
merge, or upstream submission was performed. Long-context quality, broad model
compatibility, direct-router automatic rollback, and long-duration endurance
remain explicitly unclaimed limitations.

## Current completion gates

The current native router is **not complete** until an approved GMKtek EVO-X2
maintenance window runs the current branch's
`benchmarks/swap/qualify_native_router.py`, retains its raw artifacts privately,
and records sanitized direct, warm-routed, cold-routed, alternating-model,
router-cancellation, same-model concurrency, conflicting-model queue/drain,
failed-switch rollback/accounting,
same-process re-adoption, active-reload-conflict, capacity-safe persistent residency,
TTL-eviction, unauthenticated 401, authenticated model/profile inventory,
Prometheus, and bounded router-log results. It must also run Linux real-child tests on
the current branch, then restore and health-check the protected workload. No
merge, permanent service activation, or publication of raw artifacts is
authorized by this audit.

See [integration behavior](freetoken-swap.md) and
[source research and live-test limitations](freetoken-swap-research.md).
