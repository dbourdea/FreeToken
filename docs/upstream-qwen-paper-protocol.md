# Upstream Qwen benchmark protocol evidence

## Confirmed source facts

The supplied FreeToken paper, version `2608.16157v1`, states that its main
experiments use Qwen3.6-35B-A3B, DeepSeek-V4-Flash, and GLM-5.2 on six
machines spanning an 8 GB RTX 4060 laptop through an RTX PRO 6000 workstation.
Its Table 1 reports measured host-to-device expert-transfer bandwidth (`BP`)
and measured effective CPU-side MoE expert-kernel bandwidth (`BH`), rather
than substituting vendor-link or memory specifications.

| Paper system | GPU and VRAM | CPU threads | System DRAM | PCIe | `BP` | `BH` |
| --- | --- | ---: | ---: | --- | ---: | ---: |
| 5090 desktop | RTX 5090, 32 GB | Ryzen 9 9950X3D, 32 | DDR5, 192 GiB | 5.0 x16 | 49.0 GB/s | 53.8 GB/s |
| 4060 laptop | RTX 4060 Laptop, 8 GB | Core i9-13900H, 20 | LPDDR5, 32 GiB | 4.0 x8 | 11.8 GB/s | 47.5 GB/s |

The paper states that the 8 GB laptop serves the official Qwen3.6-35B-A3B
NVFP4 release at 39.3 tokens per second in its cross-hardware coding-agent
study. It describes the 284B result as DeepSeek-V4-Flash on the 5090 desktop,
whose 32 GB RTX 5090 is paired with 192 GiB system memory. That paper system
is not a 32 GB-total-memory desktop.

The 8 GB laptop uses Qwen3.6-35B-A3B's official NVFP4 release. The other Qwen
cross-engine comparisons use BF16 for exact weight-format parity. The paper's
metrics are per-request mean decode throughput and per-request mean TTFT. Its
four workloads are AIME math reasoning, an OpenCode SWE-bench coding agent,
the same issue via Claude Code with concurrent subagents, and a 13-turn
OpenClaw email/calendar agent. The broader comparison includes llama.cpp,
Ollama, KTransformers, and MoE-Infinity.

The source repository identifies `Qwen/Qwen3.6-35B-A3B` and
`nvidia/Qwen3.6-35B-A3B-NVFP4` as known-good Qwen MoE checkpoints. Its backend
documentation defines `offload`, `cpu`, `hybrid`, and `auto`, where the latter
selects offload for MoE and may select hybrid following `ft bench bw`.

Primary sources:

- <https://arxiv.org/abs/2608.16157>
- <https://github.com/FlashML-org/FreeToken/blob/main/docs/models.md>

## Fields the paper summary does not establish

The supplied paper establishes the hardware, model format, metric type, and
workload classes. It does not identify the following fields for the 39.3 TPS
row. They must be resolved from released artifacts, the authors, or marked
unavailable before calling a GMKtec EVO-X2 result a strict replication:

| Field | State | Required action |
| --- | --- | --- |
| Checkpoint revision and exact quantization | Unknown | Inspect paper appendix, released benchmark assets, and upstream history. |
| Laptop CPU and RAM | Resolved | Core i9-13900H, 20 threads, 32 GiB LPDDR5. Record OS, driver, CUDA, and FreeToken commit if recovered. |
| Prompt corpus and token count | Workload class resolved | Locate the exact AIME questions, SWE issue, tool harness versions, and rendered token counts. |
| Output length and stop policy | Unknown | Locate benchmark runner defaults and raw results. |
| Warmup procedure and cache state | Unknown | Recover the scored-run sequence, cache state, and any discarded warmup requests from the released runner or authors. |
| TPS definition and reported statistic | Resolved at paper level | Per-request mean decode TPS and per-request mean TTFT. Retain the client-side formula and raw timestamps. |
| Expert cache, KV allocation, CPU thread count, and selected backend | Unknown | Recover the launch configuration or state that parity is approximate. |

## Current upstream benchmark source audit

On 2026-09-02, upstream `main` at
`6eca2d7d2b8576c7ad0ba62853df9f618cba929f` was inspected for released
benchmark inputs. The tree contains `benchmarks/bench_decode_moe.py`, which
implements a W1-style AIME-25 streamed OpenAI chat benchmark. It downloads
`math-ai/aime25` by default, selects problem index zero unless overridden,
performs one warm request, then records a second request. Its default measured
decode length is 256 tokens and it uses `ignore_eos` to retain that requested
step count. It records client-observed warm TTFT, decode TPS from token usage
and first-to-last content-event time, output hash, prompt-token count, and
server-reported VRAM.

This released script is a practical reproducibility aid for a current
paper-inspired W1 control. It is not proof that it is the paper's exact runner:
the paper does not name its AIME question, prompt template, request sequence,
decode budget, cache allocation, commit, or the original sampling
configuration. The inspected upstream tree does not contain a released
OpenCode SWE-bench W2 harness, Claude Code W3 harness, OpenClaw mailbox kit,
or the paper's raw benchmark artifacts. Consequently, W2 through W4 remain
unreplicable at strict-paper fidelity from public source alone.

## Current GMKtec EVO-X2 comparison status

Existing evidence proves native HIP functional serving for
`nvidia/Qwen3.6-35B-A3B-NVFP4` and a prior controlled warm output rate around
28.9 client TPS. It does not prove paper parity because the model revision,
workload, and policy contract above are incomplete. The new harness records
those differences rather than hiding them.
