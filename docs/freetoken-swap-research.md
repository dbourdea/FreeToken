# FreeToken swap compatibility and model repair

## Findings

Automatic model swapping is feasible without modifying llama.cpp or rewriting the llama-swap router. llama-swap already accepts OpenAI-compatible inference servers. FreeToken needs a compatible readiness contract, qualified model loaders, explicit resource limits, and a documented choice of process supervisor. The native daemon catalog in this branch is a useful manual control plane, but it does not itself route inference requests by model name.[1][2]

Two independent defect classes explain the unsuccessful initial attempts. First, the supervisor could report success incorrectly or time out before the model's readiness budget expired. Second, the AMD model loader and tokenizer did not support the exact resident GGUF layouts. A model catalog cannot repair a tensor format mismatch, and an HTTP listener cannot establish backend readiness. These defects need separate acceptance gates.

The implementation target remains FreeToken GitHub. The reference source is mostlygeek/llama-swap, a separate MIT-licensed project, not a component in the llama.cpp repository. The inspected reference revision is `41ec321b6216d838488b2a7d936274ed227c0c5e`. No third-party source is copied into this implementation and no upstream llama.cpp change is proposed.[1]

## How swapping should work

The intended client contract is a stable proxy URL. A request names an allowlisted model alias in its JSON `model` field. The supervisor selects that configuration, starts the corresponding backend when necessary, waits for it to accept work, and forwards the request. Subsequent requests reuse the resident backend. A request for a different model causes the routing policy to decide which process must leave memory.[1]

llama-swap's default routing is one model at a time. Its group router can explicitly make a group exclusive and require swapping among its members. Concurrent groups and the matrix router are additional capabilities, not evidence that a particular shared-memory machine has capacity to run multiple models safely. For initial GMKtek EVO-X2 qualification, an exclusive single-model policy is the appropriate starting point.[3]

There are three distinct time budgets. The readiness timeout limits how long a new backend may take to become usable. The idle TTL determines when an unused backend may be evicted. The unload timeout limits graceful process termination after eviction has begun. Increasing one does not increase the others. A short TTL can cause expensive repeated cold loads, so the example retains one model indefinitely and shows a five-minute idle TTL for the other.[4]

The assigned backend port must match the proxy target. The example passes `${PORT}` to FreeToken and explicitly proxies to `127.0.0.1:${PORT}`. It passes `${MODEL_ID}` as FreeToken's served model name so routing aliases and backend API validation agree. Catalog entries must point to already available, compatible model artifacts. The example does not download or qualify weights.[2]

Streaming is part of the acceptance contract. A proxy that buffers all generated output before replying is not equivalent to an SSE-capable model router. Tests must also cover client cancellation, admission while a model changes, concurrent requests for one model, and conflicting requests for two models. An apparently healthy proxy can still have a broken inference path; liveness and successful routing are separate measurements.

## Readiness incompatibility and repair

llama-swap polls a configured endpoint and accepts HTTP 200 as readiness. FreeToken's existing `/health` deliberately returns a diagnostic JSON document even while loading or in an error state. Consequently, pointing llama-swap at FreeToken's default `/health` can release requests before the backend is usable.[2][5]

The added `/ready` endpoint preserves `/health` compatibility. It returns HTTP 200 only when the health document reports `status=ok` and `maintenance=serving`. Loading, failure, and maintenance produce HTTP 503. The example sets `checkEndpoint: /ready`. `/v1/models` is not a substitute for this gate because listing a configured model does not prove that its weights and execution backend are ready.

The manual daemon profile path also had a stale-cache hazard. Its general health probe caches by port, but successive engines can reuse a port. A readiness check now bypasses that cache and rechecks the managed PID after the HTTP request. It also uses the launch port captured for the transaction instead of resolving a potentially changed current port afterward. This reduces false success during replacement, but it is not a request lease or a complete proof against PID reuse and unrelated port ownership.

Readiness failure returns HTTP 503 from profile operations, and the CLI returns nonzero for unsuccessful readiness responses, including responses from older servers that still use HTTP 200. The default profile transport budget is 1920 seconds, covering replacement and recovery readiness windows plus lifecycle overhead. A user-specified timeout still takes precedence. Native `switch-profile` now attempts previous-engine recovery after readiness failure, guarded by a one-use lifecycle epoch so newer operator actions win. Initial starts without a previous engine remain managed for inspection. Recovery retains the accounting safeguards and reports launch and readiness independently.

The catalog validation also rejects the `--model-path` alias and abbreviations of supervisor-owned model and port options. FreeToken uses argparse, whose default abbreviation behavior makes checking only the exact strings `--model` and `--port` insufficient. Validation remains torch-free and accepts argument vectors rather than catalog-supplied shell commands.[6]

## Model loading defects

The GGUF label Q4_K_M describes a quantization recipe, not a guarantee that every tensor is Q4_K. GGUF tensor descriptors carry their individual types. Qwen hybrid attention has independent QKV, gate, and output projections. Their packed storage cannot be concatenated blindly when the quantization block formats differ.[7][8]

The exact Qwen3.6 27B candidate contains Q6_K GDN QKV weights alongside Q4_K gate weights. The old loader attempted a packed concatenation and encountered incompatible row widths. The repair uses separate native GGUF linear operators, then combines their floating-point activations in the existing GDN computation. It does not expand the complete model to full precision.

GDN output ordering requires another repair. Quantized output blocks can span more than one value head. Moving a fraction of a block as though it were an independent head also moves or misassociates shared quantization metadata. The repaired dense path keeps the packed output weights intact and applies the inverse head-group permutation to activations before the output projection. A permutation regression test is necessary in addition to shape checks.

The first exact-file Qwen3.6 CPU/meta contract passed after applying the earlier candidate repair to an isolated AMD checkout. The same candidate did not pass Qwen3.8: its first GDN gate was Q8_0, while the candidate assumed Q4_K. This is direct evidence that a repair hardcoded for one quantization recipe should not be advertised as general Qwen support. The next iteration derives projection types from each tensor's descriptor and keeps the legacy MoE path separate.

Dense `qwen35` also needs a tokenizer converter mapping. The candidate maps it to the compatible `qwen3` converter key rather than allowing a `qwen35` dictionary lookup to fail. A real tokenizer round-trip and chat-template test remain necessary because a successful architecture lookup alone does not establish special-token behavior.

Dense checkpoints contain no routed experts. Their expert-only loading phase must be a no-op, while the separate MoE expert-cache contract must remain intact. Initial dense model qualification uses the fused/non-MoE execution selection. This should not be generalized to MoE checkpoints, which need their actual expert-residency configuration.

## Architecture decision

There are two valid operating modes, with different guarantees. In direct integration mode, a pinned llama-swap binary owns FreeToken processes and supplies automatic routing, streaming proxying, idle eviction, and its existing model-management interfaces. FreeToken supplies `/ready` and inference. The YAML example describes this mode. Do not simultaneously give those processes to `ft daemon`.

In native daemon mode, FreeToken owns process groups, durable state, and final accounting receipts. The catalog gives operators named start and switch operations with launch-failure and readiness-failure recovery. It lacks inference model routing, stream-aware admission, and idle eviction. Calling this mode a complete llama-swap replacement would overstate the implementation.

The recommended delivery sequence is to qualify the direct integration first, while retaining the native daemon catalog as a separate control-plane feature. If durable accounting is mandatory for automatically routed workloads, add a lifecycle adapter or native routing layer with explicit ownership and receipt semantics. Do not approximate that integration by letting both supervisors kill and restart the same engine. The direct example does not promise the daemon's durable accounting outbox.

Model support and runtime support must be pinned separately. This swap branch is based on the FreeToken fork's main branch, whereas the repaired Qwen loader targets its AMD branch. A model repair PR must target the AMD base rather than silently importing unrelated runtime and benchmark history into the control-plane PR. Combining branches for qualification is a local integration step, not proof that upstream FreeToken already supports the candidate.

## Qualification and operating limits

Validation proceeds from cheapest and safest checks to expensive serving tests. First parse the catalog and confirm the exact model artifact and architecture. Next validate all loader keys, shapes, and dtypes against a meta-device model. Then test tokenizer behavior and the relevant tensor-order transformations. Only after these gates should an isolated GPU process be started.

The initial GPU profile should use an explicit small sequence and token budget, such as 4096 tokens, with a bounded prefill size. FreeToken's relevant flag is `--max-seq-len-override`, not llama.cpp's `--ctx-size`. A large automatically derived cache can turn a model compatibility check into an uncontrolled capacity experiment. Successful short-context qualification does not establish 64K support.

At the current safety check, GMKtek EVO-X2 had an active llama.cpp process and approximately 23 GiB of available system memory. That process was left untouched. System `MemAvailable`, GPU-visible UMA, and current accelerator allocations are distinct measurements. A historical GPU-memory value cannot authorize a new load, and model file size alone cannot establish fit after runtime overhead, KV cache, staging, and other workloads are included.

The next real-model gate is one deterministic completion, repeated after a cold reload, with model identity and raw output retained privately. After that, test A-to-B-to-A routing, ordinary and streamed responses, cancellation, same-model concurrency, conflicting-model admission, idle eviction, forced backend failure, and shutdown. Record peak memory, swap activity, load time, time to first token, and final process cleanup. Stop a failed quality or memory-safety trial without promoting it to production.

CPU contract tests and mocked HTTP tests are valuable regression evidence, but they are not proof of GPU numerical correctness, backend graph readiness, or live swap throughput. Any release checklist must retain those distinctions. The subsequently approved maintenance-window results below supersede the initial restriction on stopping the protected service. No permanent production activation was performed.

## Completed live iterations

The repaired Qwen3.6 and Qwen3.8 files both passed their exact CPU/meta tensor contracts and tokenizer text round-trips. Twenty-one model tests passed, including a matrix of independently typed QKV/gate projections. The daemon suite passed 52 tests with two platform skips; the AMD benchmark/privacy suite passed 27 tests.

The first live startup problem was a qualification-command error: `python -m freetoken` is the legacy direct-server entrypoint and rejects the `serve` subcommand. The corrected invocation is `python -m freetoken.cli serve`. Another attempt stalled behind an abandoned shared PyTorch extension-cache lock. The solution was a private `TORCH_EXTENSIONS_DIR` and native-kernel preflight before stopping the protected service. The shared cache was left untouched.

Two complete A-to-B-to-A passes then succeeded through the pinned, unmodified llama-swap binary. The extended pass returned the deterministic answer `4` for Qwen3.6, Qwen3.8, then Qwen3.6 in 35.99, 44.17, and 33.17 seconds, including loading or switching. It also passed two concurrent requests for the same model, concurrent requests for different models, explicit streamed usage blocks, and five-second idle eviction. These are bounded functional controls, not broad quality benchmarks or isolated decode-throughput measurements.

Both ordinary and SSE responses were checked, including `[DONE]`. Adding `stream_options: {"include_usage": true}` eliminated the missing-usage metrics issue without changing llama-swap. The original stream was valid JSON but lacked the usage block that its metrics parser requires. The final proxy/backend log contained no recorded traceback or streaming-metrics error.

Every maintenance trial restored the protected service and verified a deterministic completion. After the final pass, the service manager reported it active and running, and the test listeners were closed. Raw artifacts remain private under the logical sets `freetoken-swap-live-20260910-d` and `freetoken-swap-live-20260910-e`. FreeToken PR #1 contains the control-plane integration and PR #2 contains the AMD model repair and anonymization.

Remaining limits are explicit: no claim of long-context qualification, comprehensive tool-calling quality, cancellation coverage, direct-supervisor rollback, or long-duration reliability is made. Native daemon rollback has CPU failure-injection and HTTP integration coverage, not GPU failure-recovery qualification. The direct integration does not acquire the daemon's durable accounting guarantees. Semaphore-cleanup warnings remain a follow-up investigation even though the service recovery and port cleanup checks passed.

### Native recovery regression suite

The additional Linux real-process suite passes both normal SIGTERM and SIGTERM-resistant child cases on GMKtek EVO-X2, without loading models or interrupting the protected workload. It uses isolated loopback HTTP test children and verifies previous-engine readiness recovery, restored arguments and pidfile, two durable replacement receipts, process-group worker cleanup, and a closed listening port. This strengthens OS lifecycle evidence but is not GPU model-failure qualification.

The daemon suite passes 69 tests with 2 platform skips. Added coverage exercises replacement launch failure, recovery launch failure, readiness error and timeout, recovery readiness failure, accounting failure preservation, replacement exit and persisted-state cleanup, one-use recovery tickets, and invalidation by newer lifecycle operations. An HTTP integration test blocks the only proxy worker during readiness and confirms that an operator stop completes through the separate lifecycle worker without triggering stale recovery. These are controlled CPU tests with fake child processes, not new real-model measurements.

## Privacy and publication

Public material identifies the primary test computer as GMKtek EVO-X2. Personal home paths use `/home/operator` or equivalent placeholders, and LAN addresses use documentation-only example addresses. Raw logs remain private because they may contain personal paths, hostnames, device identifiers, and request content. Redaction must not make an example address appear to be a working deployment address.

Privacy review preserves license notices, upstream authorship, and repository URLs needed for provenance. Working-tree sanitation does not remove identifiers from historical Git objects, forks, cached PR revisions, or previously generated PDFs. History rewriting and regenerated publication artifacts require a separate, verified pass; they must not be reported as completed merely because current Markdown has been sanitized.

## Sources

Sources were inspected on 2026-09-10. Local implementation and test observations above refer to the candidate branches, not to claims made by upstream maintainers.

1. mostlygeek/llama-swap contributors. [Repository and feature overview](https://github.com/mostlygeek/llama-swap/tree/41ec321b6216d838488b2a7d936274ed227c0c5e), pinned revision; MIT license in `LICENSE.md`.
2. mostlygeek/llama-swap contributors. [Writing the cmd for a model](https://github.com/mostlygeek/llama-swap/blob/41ec321b6216d838488b2a7d936274ed227c0c5e/docs/kb/guides/model-runtime/writing-cmd.md), updated 2026-08-25. Port assignment, readiness, and model-name rewriting.
3. mostlygeek/llama-swap contributors. [Running several models at once with groups and matrix](https://github.com/mostlygeek/llama-swap/blob/41ec321b6216d838488b2a7d936274ed227c0c5e/docs/kb/guides/routing/groups-and-matrix.md), updated 2026-08-25.
4. mostlygeek/llama-swap contributors. [Automatic model unloading with ttl](https://github.com/mostlygeek/llama-swap/blob/41ec321b6216d838488b2a7d936274ed227c0c5e/docs/kb/guides/model-runtime/ttl-and-unloading.md), updated 2026-08-25.
5. FreeToken contributors. [Control API](../python/freetoken/server/control_api.py), `build_health` and `register_control_routes` in the candidate checkout.
6. FreeToken contributors. [Server argument parser](../python/freetoken/server/args.py), model aliases and parser construction in the candidate checkout.
7. ggml-org/llama.cpp contributors. [Qwen35 model implementation](https://github.com/ggml-org/llama.cpp/blob/master/src/models/qwen35.cpp). Independent attention/gate model structure; moving upstream reference, not a candidate qualification result.
8. ggml-org/llama.cpp contributors. [Quantization recipes discussion](https://github.com/ggml-org/llama.cpp/discussions/20522). Primary maintainer discussion of per-tensor quantization choices; not evidence that every file using the same recipe has identical layouts.
