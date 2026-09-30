# FreeToken native swap final qualification — 2026-09-23

This record supersedes earlier statements that current-engine GMKtek EVO-X2 evidence was still missing. Raw paths, credentials, prompts, responses, process identifiers, and host-specific artifacts remain private.

## Qualified source

- FreeToken source commit: `56e0232` (`feat(daemon): qualify native model swapping on AMD`).
- Draft review: `dbourdea/FreeToken` PR 4, from `codex/freetoken-swap-amd` to `main`.
- Read-only reference: `mostlygeek/llama-swap` commit `41ec321b6216d838488b2a7d936274ed227c0c5e`, MIT licensed.
- No llama-swap or llama.cpp source was modified or submitted.

## Deterministic and repository evidence

- Changed-file Ruff checks passed.
- The focused daemon, router, metrics, qualification, and Qwen GGUF configuration suites passed: **183 passed**.
- The complete repository run reported **1947 passed, 81 skipped, and 21 failed**.
- Every one of the 21 failures reproduced at the parent commit on the same environment. They are baseline platform/dependency failures outside the changed daemon, router, metrics, qualification, and Qwen 3.5/3.6 GGUF files; they are not presented as a green full-suite result.
- Python compilation and `git diff --check` passed before commit.

## Private live two-model matrix

The final private qualification result recorded `passed: true`, `restored: true`, no primary error, no cleanup error, and no restoration error. The same run behaviorally proved:

| Capability | Sanitized result |
| --- | --- |
| Direct, warm, cold, and A-B-A routing | Passed with distinct measurements and correct model identity. |
| Aliases, configured readiness, upstream model rewrite, selectors, and startup profile | Passed. |
| OpenAI-compatible ordinary and SSE proxying | Passed, including terminal stream handling and usage-backed performance collection. |
| Authentication | Unauthenticated inference and management were rejected; Bearer, Basic-password, and `X-Api-Key` succeeded. |
| Same-model concurrency and conflicting-model drain | Passed without overlapping owned engines or killing an active request. |
| Explicit cancellation | Passed with terminal abort, lease release, and cancellation accounting on the same daemon instance. |
| Failed switch and rollback | Passed with a visible failure, durable accounting evidence, restored prior model, and a successful restored completion. |
| Restart and re-adoption | Passed with exact persisted process identity and no duplicate runner. |
| Reload conflict | Passed; active lifecycle redefinition was rejected atomically. |
| Capacity-safe persistence and TTL eviction | Passed under the declared one-resident capacity policy. |
| Metrics, logs, activity, and hardware telemetry | Passed; owned-process RAM and AMD VRAM/GTT were positive and source-labelled. |
| Cleanup and protected-workload restoration | Passed with no qualification listeners or engines left behind. |

## Production migration evidence

The legacy model runner and its model-specific watchdog timer were disabled, and the model-specific cache cron entry was removed. Their prior units and crontab were backed up before modification. The generic thermal watchdog and unrelated backup workflow were preserved.

One user-level `freetoken-swap.service` now owns the native daemon and exactly one model engine. The service:

- is enabled under the lingering user `default.target`;
- binds the stable LAN control/inference port while engine ports remain loopback-only and dynamically allocated;
- applies the validated power profile before launch;
- uses a private extension cache and a mode-600 catalog/API key;
- preloads the qualified GPT-OSS model because it starts reliably inside the bounded boot gate;
- keeps the qualified Qwen GGUF available for routed on-demand swapping;
- stops its owned engine with the daemon and has no second model supervisor.

A real reboot changed the boot identifier and then produced all of the following without a login or manual action:

- the service became enabled and active;
- the startup profile became active;
- `model-b` was readiness-gated resident with exact identity matching;
- unauthenticated model listing returned 401;
- authenticated health returned 200 with `engineRunning: true`;
- an authenticated deterministic completion returned exactly `4` from `model-b`;
- owned-process telemetry reported approximately 14.5 GB of AMD VRAM/GTT and positive process RAM;
- the stable port was reachable from another LAN computer;
- the retired service and timer remained disabled and inactive.

The first reboot exposed and corrected a systemd ordering cycle caused by requiring a watchdog that itself ordered after `default.target`. The corrected unit requests the watchdog without ordering the model service after it. A second real reboot proved the fix.

## Compatibility disposition

Applicable pinned-reference behavior is implemented and behaviorally evidenced for FreeToken's text-generation backend. Unsupported embeddings, rerank, image, speech, transcription, SDAPI, and ComfyUI routes remain intentionally inapplicable because FreeToken has no matching backend. MCP, Tailcat, and remote peer transport remain explicit future product expansions, not fabricated parity. Multi-resident matrix solving remains inapplicable under the declared one-engine ownership policy; the implemented equivalent is exclusive capacity, protected persistence, FIFO/priority admission, and deterministic eviction.

## Release disposition

The source is published only as a **draft** FreeToken pull request. It is not merged. Raw operational artifacts remain private. This evidence closes the current-engine, GPU-model, restoration, and unattended-startup gates for the qualified GMKtek EVO-X2 configuration; it does not claim broad model-family quality, long-context quality, or multi-host peer support.