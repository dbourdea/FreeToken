# freetoken-swap: named, safe model switching

The native `ft daemon` catalog currently provides **manual** named-model switching. It is not yet an automatic inference router. It keeps FreeToken's native lifecycle transaction and deliberately does not run shell commands from catalog entries. One daemon supervises one `ft serve` process at a time, so a model replacement is serialized with accounting, graceful drain, process-group cleanup, durable state, and the existing health endpoints.

For automatic request routing, the integration path is an unmodified, pinned llama-swap binary supervising FreeToken directly, using the new `/ready` endpoint. See [the example](../examples/freetoken-swap.yaml) and [compatibility research](freetoken-swap-research.md). This direct mode does not use the daemon's durable accounting outbox. Do not let both supervisors manage the same process or port. Real-model swap qualification remains required before production use.

The catalog is TOML and is optional. Start the daemon with `--catalog` or set `FREETOKEN_SWAP_CATALOG`:

```toml
[models.qwen-coder]
model = "/models/Qwen3-Coder-30B-A3B-Q4_K_M.gguf"
port = 1922
args = ["--max-seq-len-override", "4096", "--num-tokens", "4096"]
description = "GMKtek EVO-X2 candidate coding profile"
ready_timeout_s = 300

[models.qwen-chat]
model = "/models/Qwen3.5-27B-Q4_K_M.gguf"
args = ["--max-seq-len-override", "4096", "--num-tokens", "4096"]
```

```bash
ft daemon --catalog /etc/freetoken/models.toml
ft daemon models
ft daemon start-profile qwen-coder
ft daemon switch-profile qwen-chat
ft daemon health
```

`GET /models`, `POST /engine/start-profile`, and `POST /engine/switch-profile` expose the same control-plane capability. They require `X-FT-Token` whenever the daemon has a token configured. Use `switch-profile --force` only for the same recovery case as `ft daemon switch --force`: the final accounting receipt may be incomplete when a failed engine cannot be observed.

Profiles accept only `model`, `port`, `args`, `description`, and `ready_timeout_s` (default 120 seconds). `args` is passed as an argument vector to `ft serve`; it is never interpreted by a shell. A profile cannot set `--model` or `--port` in `args`, because those fields are owned by the supervisor and are part of its conflict and re-adoption identity. The model files and catalog remain local operational configuration, not repository content.

These are illustrative paths, not a list of qualified models. In particular, dense Qwen GGUF support requires a compatible AMD/model-loader branch and cannot be inferred from this control-plane PR.

After a profile launch, the daemon polls uncached engine health, verifies the process identity again after each probe, and waits for `status=ok` and `maintenance=serving`. Readiness failure returns HTTP 503. The client returns a nonzero exit code and defaults to a 1920-second transport budget, covering two maximum 900-second readiness windows plus lifecycle overhead. A user-specified client timeout still takes precedence.

For `switch-profile`, readiness failure attempts to restore the exact previous engine and probes its readiness using a second window of the requested profile's `ready_timeout_s`. The response remains HTTP 503 because the requested replacement failed, with a separate `rollback.readiness` result. Recovery is single-use and invalidated by any newer start, stop, switch, or shutdown. HTTP probing releases the lifecycle lock and runs in the proxy pool, so an operator can stop a loading engine without waiting for the readiness timeout. Accounting failure during recovery preserves the failed engine instead of silently forcing cleanup. An initial `start-profile` or a switch with no previous engine leaves the failed process managed for diagnosis. These policies do not change the direct llama-swap supervisor.

If a replacement launch raises before an owned child exists, the daemon attempts to relaunch the previous model with its exact port and arguments, under the same lifecycle transaction. Both switch endpoints return HTTP 503 with `code=switch_launch_failed`, the original accounting receipt, and a `rollback` result. `rollback.launched` means only that the recovery process launched, not that it is ready. A failed recovery is reported explicitly. Accounting failures before stop preserve the original engine; a post-spawn failure that leaves an owned child does not trigger a second launch. These safeguards apply to daemon switches, not the separate direct llama-swap supervisor.

FreeToken's `/health` remains a backwards-compatible diagnostic endpoint and can return HTTP 200 while loading or failed. `/ready` returns HTTP 503 for loading, failure, or maintenance, and HTTP 200 only when accepting requests. Configure llama-swap with `checkEndpoint: /ready`, never `/health` or `/v1/models` as a substitute.

Use `ft serve` or `python -m freetoken.cli serve` in a process command. The legacy `python -m freetoken` entrypoint does not accept the `serve` subcommand. Use a revision-specific `TORCH_EXTENSIONS_DIR` and prebuild native GGUF kernels before a maintenance window so an abandoned shared build lock cannot stall model initialization. For SSE token metrics, clients should request `stream_options: {"include_usage": true}`.

## Cancellation qualification

The opt-in Linux harness `benchmarks/swap/qualify.py --cancellation` adds a live disconnect gate to its maintenance-window run. It reads SSE incrementally, verifies that generation is active, closes the response after the first content delta, and polls backend statistics through `/upstream/model-a/v1/stats`. Passing requires the same backend instance to become idle without increasing the normal-completion count. A backend restart, an already-finished response, or a missing terminal abort fails the gate. It then checks fresh A-to-B-to-A streaming completions. Prefix bytes, backend snapshots, first-content timing, abort latency, and recovery responses are private artifacts.

The gate passed against the real Qwen3.6 GPU workload on GMKtek EVO-X2 in an approved maintenance window. The same backend changed from one active request to zero, with its normal-completion count unchanged. Observed first content was 0.368 seconds and terminal abort was observed 0.254 seconds after disconnect. Post-cancellation A-to-B-to-A streaming, concurrent routing, idle eviction, and protected-service restoration also passed. This is one bounded cancellation case, not a cancellation endurance benchmark. Use `--extended` as well to retain concurrent-request and TTL gates. Existing mandatory source, model, protected-service, and artifact arguments still apply; `--allow-maintenance` is not a substitute for operator approval.

## Native model-failure recovery qualification

`benchmarks/swap/qualify_native_recovery.py` exercises the actual daemon profile endpoints with real FreeToken child processes. It starts the supplied model, verifies generation, switches to a deliberately invalid GGUF fixture in its private artifact directory, checks the HTTP 503 response and automatic recovery readiness, then verifies streamed generation from the restored model. The real Qwen3.6 run passed after the loader reported `GGUF magic invalid`. The original engine's sealed accounting receipt was complete; the failed loader's crash receipt was explicitly degraded with unknown token totals. Cleanup and restoration of the protected llama.cpp workload passed.

The harness accepts separate `--source` and `--daemon-source` paths so the AMD runtime and the swap feature branch can be tested together without modifying a live checkout. `--extensions-dir` must identify a private cache prebuilt from the selected runtime source. Required arguments also include `--python`, `--model`, `--protected-service`, `--protected-url`, `--artifacts`, and `--allow-maintenance`. The fixture never replaces an existing model. Raw logs and result files contain private deployment details and must not be published unreviewed.

## Provenance and scope

The design was informed by [mostlygeek/llama-swap](https://github.com/mostlygeek/llama-swap), checked out locally at `41ec321b6216d838488b2a7d936274ed227c0c5e` on 2026-09-10. llama-swap is MIT licensed (`LICENSE.md`). No llama-swap or llama.cpp code is vendored, modified, or submitted by this feature. FreeToken remains the sole change and pull-request target.
