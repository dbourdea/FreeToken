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

## Provenance and scope

The design was informed by [mostlygeek/llama-swap](https://github.com/mostlygeek/llama-swap), checked out locally at `41ec321b6216d838488b2a7d936274ed227c0c5e` on 2026-09-10. llama-swap is MIT licensed (`LICENSE.md`). No llama-swap or llama.cpp code is vendored, modified, or submitted by this feature. FreeToken remains the sole change and pull-request target.
