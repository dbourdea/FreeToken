# FreeToken swap completion audit

This audit preserves the full integration goal. A draft PR and passing CPU tests
do not establish that every lifecycle behavior is qualified on real models.

## Combined source verification

- Swap source: `64dcc683d4e767fb4af8b7088ebb58564b1b7535`.
- AMD model-repair source: `de23ad6a9e74aecc72b9f6b9e81b8c3376ff2e60`.
- Git's clean merge-tree result: `c3c0ae54a09857b98bba83cfc75b91264e6eeb43`.
- The combined tree was archived into an isolated temporary directory on
  GMKtek EVO-X2. Neither branch nor the live runtime was replaced by that tree.
- Linux validation: 114 daemon, privacy, benchmark, and reproducibility tests
  passed, including the real child-process recovery tests. No skips.
- Combined-tree Qwen validation: 21 grouped-output, SSM, and config tests passed.
- The protected llama.cpp service remained active throughout these CPU checks.

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

## Requirement evidence and gaps

| Requirement | Evidence | Status |
| --- | --- | --- |
| Official source, license, and provenance | Read-only llama-swap reference pinned to `41ec321b6216d838488b2a7d936274ed227c0c5e`, MIT license; research report and configuration example | Documented |
| Model catalog and lifecycle controls | Validated TOML catalog, authenticated profile endpoints, native process manager | Implemented and CPU-tested |
| Automatic model routing | Native `freetoken-swap` model-ID admission, readiness-gated activation, request-preserving proxying, cancellation, TTL eviction, reload, and deterministic HTTP tests; prior direct llama-swap runs remain comparison evidence only | Implemented and CPU/HTTP tested; native real-engine qualification remains required |
| Readiness and API compatibility | Separate `/ready`, uncached generation-aware profile checks, ordinary and SSE completions | CPU and bounded live evidence |
| Concurrency and unloading | Prior same-model and conflicting-model concurrent requests plus idle eviction | Bounded live verification passed |
| Rollback protections | Launch/readiness recovery, newer lifecycle intent wins, accounting preservation, actual Linux process-group tests; real invalid-GGUF failure followed by Qwen3.6 readiness and generation recovery | Implemented and bounded live verification passed |
| Client cancellation | Native opaque router request IDs, active-request list, explicit cancel endpoint, upstream socket close, lease release, and cancellation metrics; prior direct-mode same-instance test | Implemented and deterministic HTTP tested; native same-instance GPU verification remains required |
| Model compatibility | Mixed-format Qwen/GDN repair, tokenizer checks, exact-model contracts, prior live completion evidence, 21 combined-tree model tests | Qualified only for documented models and bounded workloads |
| Production protection | Isolated test paths, explicit maintenance gate, prior restore and completion checks, no interruption during combined-tree checks | Maintained |
| Privacy | Generic GMKtek EVO-X2 label, sanitized public metadata and examples, privacy regressions, regenerated reviewed PDF | Current publication changes sanitized; historical copies not erased |
| FreeToken-only publication | Draft PRs 1 and 2 in `dbourdea/FreeToken`; both reported mergeable | Submitted, not merged |

The PRs target different base branches: PR 1 targets `main`; PR 2 targets
`amd-rocm-gfx1151`. The clean combined tree is compatibility evidence, not an
instruction to merge either PR or change the repository's release strategy.
GitHub reported no status checks for either PR at this audit. The test results
above are independently executed evidence, not claims of passing hosted CI.

## Final live completion gates

The user approved another maintenance window. Both live gates passed:

1. GPU stream cancellation reached terminal idle on the same backend, without
   a normal-completion increment. Post-disconnect A-to-B-to-A streaming,
   concurrency, and TTL unloading passed.
2. Native daemon recovery passed after the real loader rejected an invalid
   GGUF fixture. The restored Qwen3.6 model reached readiness and generated the
   expected answer. The failed switch correctly remained HTTP 503.
3. Both phases restored and health-checked the protected service, including a
   verified completion. Final process/listener checks found no test runtime
   remaining. The accounting gap for the crashed loader is explicitly degraded.

The approved window is closed. No permanent production activation, merge, or
upstream submission was performed. The PRs remain drafts for maintainer review;
submission and verification do not authorize merging or production promotion.
Long-context quality, broad model compatibility, direct-router automatic
rollback, and long-duration endurance remain explicitly unclaimed limitations,
not capabilities inferred from these bounded tests.

See [integration behavior](freetoken-swap.md) and
[source research and live-test limitations](freetoken-swap-research.md).
