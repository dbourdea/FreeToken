# Dense Qwen GGUF swap validation

This candidate targets the FreeToken AMD branch. It supports the resident Qwen3.6 27B and Qwen3.8 27B Q4_K_M layouts by retaining independent packed projection types, restoring GDN value-head order, and mapping dense `qwen35` tokenizer metadata. It is not a general qualification of every Qwen checkpoint or quantization recipe.

## Repair

The old loader concatenated packed QKV and gate tensors even when their row-byte formats differed. The dense path now takes each attention/GDN projection type from the GGUF tensor descriptors and constructs separate native operators. This is required for both Q6_K/Q4_K and Q8_0 gate combinations. Full-attention Q, K, and V also retain their separate formats.

GDN output weights remain byte-exact in their quantized blocks. The activation is regrouped before the output projection rather than attempting to move part of a quantization block. The legacy MoE fused-QKV path and its expert-cache ownership remain separate. A dense expert-only load phase is an intentional no-op.

The change preserves unrelated current model configuration fields, including other model families' configuration payloads. Reusing an older candidate's complete configuration file would have removed those fields, so only the new GGUF descriptor field is added to the current base.

## Verified results

Tests were run on GMKtek EVO-X2 using an isolated source checkout, not the protected inference service's files.

The model SHA-256 checksums were independently verified after testing:

- Qwen3.6-27B-Q4_K_M.gguf: `33625d8dc3a5dd8d88c324d47db58561b11f7072816287078bfe58b4c55782f9`.
- Qwen3.8-27B-Q4_K_M.gguf: `31629f53165ab6a7dad8c9847dcfd1fdf55829dac1e6e748f4a68581b0033d34`.

| Gate | Result |
| --- | --- |
| Model metadata, GDN packing combinations, head-order tests | 21 passed |
| Qwen3.6 exact tensor-name/shape/dtype contract | Passed on CPU/meta |
| Qwen3.8 exact tensor-name/shape/dtype contract | Passed on CPU/meta |
| Qwen3.6 tokenizer text round-trip | Passed |
| Qwen3.8 tokenizer text round-trip | Passed |
| Public-document privacy and benchmark regression tests | 27 passed |
| Qwen3.6 through llama-swap, ordinary response | `4`, 39.00 seconds including load |
| Switch to Qwen3.8, SSE response | `4` and `[DONE]`, 41.10 seconds including switch |
| Switch back to Qwen3.6, SSE response | `4` and `[DONE]`, 38.25 seconds including switch |
| Protected service restoration | Health and deterministic completion passed |

A second, extended pass repeated A-to-B-to-A successfully in 35.99, 44.17, and 33.17 seconds. It also passed same-model concurrent requests, different-model concurrent requests, streamed usage-block checks, and five-second idle eviction. The private artifact set is `freetoken-swap-live-20260910-e`. The protected service was restored and verified, and the candidate listeners were closed. These timings include load/switch overhead and should not be used as decode throughput.

The three live requests used temperature 0 and a 32-token output limit. Each asked for the single-digit answer to 2 + 2. These are deterministic smoke tests, not a broad reasoning benchmark. The request durations include model startup or switching and are not decode throughput or isolated time-to-first-token measurements.

The runtime used a 4096-token sequence limit, 4096-token cache allocation, 512-token prefill bound, one concurrent backend request, graph batch size 1, Triton attention, fused dense execution, and disabled PyNCCL. The Qwen3.6 cache allocation was 0.25 GiB. This does not establish 64K operation, multi-GPU support, or MoE checkpoint quality.

## Swap integration requirements

The successful live run used an unmodified llama-swap binary built from `41ec321b6216d838488b2a7d936274ed227c0c5e`, plus FreeToken's `/ready` endpoint from the separate swap control-plane PR. The latter returns HTTP 503 while loading and 200 when accepting requests. FreeToken's diagnostic `/health` alone is not a compatible llama-swap readiness signal.

The real Python CLI module is `python -m freetoken.cli serve`. The legacy `python -m freetoken` entrypoint starts a server directly and does not accept the `serve` subcommand. A configuration that mixes those forms exits during argument parsing.

Each qualification run used its own `TORCH_EXTENSIONS_DIR`. A stale lock in the shared extension cache had caused a graph-preparation stall; the shared cache was not deleted or modified. GGUF kernels were then compiled and imported in the private cache before the protected service was stopped. The host extensions were built from the isolated source, rather than copied from an unverified checkout.

For streamed token metrics, request `stream_options: {"include_usage": true}`. A valid stream without a usage block can still generate llama-swap's misleading metrics warning about missing valid JSON. The generated content and `[DONE]` framing passed in the initial run; usage reporting is a separate integration check.

## Evidence and remaining limits

The private artifact set `freetoken-swap-live-20260910-d` contains the configuration, native kernel build log, proxy/backend log, three raw responses, baseline response, recovery response, and structured results. These raw artifacts are intentionally not committed because they include operational paths and process details.

This candidate still requires broader quality testing, cancellation and recovery testing, and a longer reliability run before production promotion. Existing semaphore-cleanup warnings should be investigated separately. No production configuration was changed or permanently activated, and no change was submitted to llama.cpp or llama-swap.

## Privacy

Current public AMD reports use GMKtek EVO-X2, placeholder operator paths, and documentation-only IP addresses. Benchmark launchers derive the invoking user's home directory instead of embedding a personal username; most root-directory defaults also accept `FREETOKEN_ROOT_DIR`. When invoking under a different account, explicitly set the intended root directory. Historical commits and previously generated binary publications are not erased by these working-tree changes.

Benchmark API clients now require `--expected-host`; host-specific shell wrappers require an explicitly configured `FREETOKEN_EXPECTED_HOST` where they previously embedded the machine hostname. This preserves the host safety check and fails closed if no target is selected. Manuscript contact metadata and the tracked review PDF are anonymized in this branch. Repository-owner URLs, licenses, and third-party attribution remain intact. The separate checkout's in-progress manuscript and PDF edits are preserved, not overwritten by this review copy.
