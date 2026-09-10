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
| Automatic model routing | Unmodified llama-swap directly supervising FreeToken; prior real Qwen A-to-B-to-A runs | Bounded live verification passed |
| Readiness and API compatibility | Separate `/ready`, uncached generation-aware profile checks, ordinary and SSE completions | CPU and bounded live evidence |
| Concurrency and unloading | Prior same-model and conflicting-model concurrent requests plus idle eviction | Bounded live verification passed |
| Rollback protections | Launch/readiness recovery, newer lifecycle intent wins, accounting preservation, actual Linux process-group tests | Implemented; real-model failure recovery still unqualified |
| Client cancellation | Strict disconnect gate and real localhost transport test | Harness verified; FreeToken GPU cancellation still unqualified |
| Model compatibility | Mixed-format Qwen/GDN repair, tokenizer checks, exact-model contracts, prior live completion evidence, 21 combined-tree model tests | Qualified only for documented models and bounded workloads |
| Production protection | Isolated test paths, explicit maintenance gate, prior restore and completion checks, no interruption during combined-tree checks | Maintained |
| Privacy | Generic GMKtek EVO-X2 label, sanitized public metadata and examples, privacy regressions, regenerated reviewed PDF | Current publication changes sanitized; historical copies not erased |
| FreeToken-only publication | Draft PRs 1 and 2 in `dbourdea/FreeToken`; both reported mergeable | Submitted, not merged |

The PRs target different base branches: PR 1 targets `main`; PR 2 targets
`amd-rocm-gfx1151`. The clean combined tree is compatibility evidence, not an
instruction to merge either PR or change the repository's release strategy.
GitHub reported no status checks for either PR at this audit. The test results
above are independently executed evidence, not claims of passing hosted CI.

## Remaining completion gates

1. In an approved isolated maintenance window, run the real FreeToken
   cancellation gate and verify post-disconnect A-to-B-to-A routing.
2. Qualify native daemon recovery from a real replacement-model failure,
   including restored-model readiness and completion, not merely a new PID.
3. Review the complete evidence after those runs, including cleanup, protected
   service restoration, and any newly exposed defects. Keep the PRs as drafts
   until the required reliability evidence supports promotion.

The earlier maintenance window is closed. A new window has been requested but
is not assumed approved. These remaining tests must not stop or compete with
the protected workload without that approval. Long-context and broad model
quality claims remain outside the bounded results and must not be inferred.

See [integration behavior](freetoken-swap.md) and
[source research and live-test limitations](freetoken-swap-research.md).
