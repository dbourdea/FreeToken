# freetoken-swap: named, safe model switching

`freetoken-swap` is FreeToken's named-model layer over `ft daemon`. It takes the useful model catalog workflow from llama-swap, but keeps FreeToken's native lifecycle transaction and deliberately does not run shell commands from catalog entries. One daemon supervises one `ft serve` process at a time, so a model replacement is serialized with accounting, graceful drain, process-group cleanup, durable state, and the existing health endpoints.

The catalog is TOML and is optional. Start the daemon with `--catalog` or set `FREETOKEN_SWAP_CATALOG`:

```toml
[models.qwen-coder]
model = "/models/Qwen3-Coder-30B-A3B-Q4_K_M.gguf"
port = 1922
args = ["--ctx-size", "32768", "--gpu", "GPU-EXAMPLE"]
description = "Strix Halo coding profile"

[models.qwen-chat]
model = "/models/Qwen3.5-27B-Q4_K_M.gguf"
args = ["--ctx-size", "16384"]
```

```bash
ft daemon --catalog /etc/freetoken/models.toml
ft daemon models
ft daemon start-profile qwen-coder
ft daemon switch-profile qwen-chat
ft daemon health
```

`GET /models`, `POST /engine/start-profile`, and `POST /engine/switch-profile` expose the same control-plane capability. They require `X-FT-Token` whenever the daemon has a token configured. Use `switch-profile --force` only for the same recovery case as `ft daemon switch --force`: the final accounting receipt may be incomplete when a failed engine cannot be observed.

Profiles accept only `model`, `port`, `args`, and `description`. `args` is passed as an argument vector to `ft serve`; it is never interpreted by a shell. A profile cannot set `--model` or `--port` in `args`, because those fields are owned by the supervisor and are part of its conflict and re-adoption identity. The model files and catalog remain local operational configuration, not repository content.

## Provenance and scope

The design was informed by [mostlygeek/llama-swap](https://github.com/mostlygeek/llama-swap), checked out locally at `41ec321b6216d838488b2a7d936274ed227c0c5e` on 2026-09-10. llama-swap is MIT licensed (`LICENSE.md`). No llama-swap or llama.cpp code is vendored, modified, or submitted by this feature. FreeToken remains the sole change and pull-request target.
