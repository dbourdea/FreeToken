# freetoken-swap parity matrix

This is the implementation acceptance contract for native `freetoken-swap`.
It is based on the read-only official llama-swap reference at commit
`41ec321b6216d838488b2a7d936274ed227c0c5e`, MIT licensed. It does not copy
that project's code or authorize changes outside FreeToken.

Status labels:

- **Native**: implemented by FreeToken and behaviorally tested.
- **Integrated only**: available only when an unmodified llama-swap binary
  supervises FreeToken. This is not native parity.
- **Missing**: applicable, not yet implemented.
- **Inapplicable**: the current FreeToken server lacks the corresponding
  backend modality. The absent route is named explicitly rather than claimed.

| Pinned llama-swap capability | Current FreeToken state | Required native parity evidence |
| --- | --- | --- |
| Model catalog and aliases | Native TOML catalog with validated model, port, args, readiness, unload, and upstream response timeouts | Documented YAML-to-TOML translation and atomic reload exist. Dynamic port allocation and native selector transforms remain missing. |
| Start, stop, switch, PID identity, re-adoption | Native and tested | Preserve as router substrate; exercise automatic-request ownership |
| Readiness and diagnostic health | Native `/ready` plus diagnostic `/health` | Preserve exact HTTP behavior through the unified router |
| Automatic OpenAI model-ID routing | Native single-engine coordinator with priority-aware admission and health-gated activation | `tests/daemon/test_router.py` covers cold activation, same-model concurrent leases, safe swap waiting, and unknown-model errors. Linux and GMKtek EVO-X2 evidence remains required. |
| OpenAI completion and chat completion forwarding | Native request-byte-preserving proxy, including SSE body forwarding | Deterministic mocked and real-loopback HTTP tests cover `/v1/chat/completions`, request bytes, SSE bytes, headers, and lease release. Direct, cold, warm, cancellation, and performance evidence remains required. |
| OpenAI Responses endpoint | Native route uses the same admission and proxy contract | Add explicit cancellation and response-object lifecycle proof. |
| Anthropic Messages and token-count routing | Native routes use the same admission and proxy contract | Deterministic HTTP Messages test exists; add token-count and live failure proof. |
| Unknown-model status and direct upstream access | Native stable unknown-model error and `/upstream/{profile}/...` passthrough through the same lease | Deterministic tests cover GET passthrough, query forwarding, and rejection of unsafe direct `prepare-stop`; add real-engine coverage. |
| FIFO, priority, exclusive group routing | Native priority-aware FIFO queue and one-engine exclusive admission | Add concurrent priority ordering and group transition tests against a real engine. |
| Matrix capacity policy and eviction costs | Native explicit one-resident-model policy exposes active group, resident model, available slots, and eviction counters | Multi-resident matrix solving and memory-qualified eviction cost selection are missing. |
| Persistent resident models | Native persistent group protects the sole resident slot until explicit unload | Deterministic capacity-protection test exists. Multi-resident preload is unavailable with the current one-engine supervisor. |
| TTL and unload timeout | Integrated only | Native timer, explicit unload, process cleanup and accounting tests |
| Load/unload management API and running-model list | Native router status, configured plus resident `/router/models`, explicit unload, engine lifecycle controls | Add load-all or multi-resident management only when the supervisor supports more than one engine. |
| Profiles | Native `/router/profiles`, configured model catalog, and profile activation through routed request or existing explicit engine controls | Add a documented profile-transform policy beyond alias selection if FreeToken needs it. |
| API keys | Native daemon token, different header and scope | Router inference and management key policy with authorization tests |
| Logs and bounded streaming logs | Native engine log snapshot only | Bounded router/proxy/upstream log buffers and SSE log streams |
| Prometheus and activity/performance metrics | Native `/metrics` exposes bounded router admission, queue, activation, failure, cancellation, eviction, terminal-stream, last-TTFT, and last-duration signals; engine metrics remain separately available | Add throughput, process, and memory measurements with direct/cold/warm/alternating benchmark evidence. |
| Inflight cancellation API | Native router issues or accepts opaque `X-FT-Request-ID` values, lists active IDs, and provides `POST /router/requests/{id}/cancel` | Deterministic blocked-stream test proves socket close, lease release, and cancellation metric. Same-instance real-engine terminal-abort proof remains required. |
| Parameter filters and configuration hooks | Native profile `drop_fields` removes explicitly configured safe top-level JSON fields only; default forwarding preserves original bytes | Arbitrary set-parameter transforms and lifecycle shell hooks are intentionally unsupported for safety. |
| Configuration watch/reload | Native authenticated `POST /router/reload` re-parses the catalog atomically | Deterministic tests cover valid replacement, invalid-file rejection, and active-profile redefinition refusal. File watching and real-engine reload evidence remain required. |
| UI, hardware, captures, MCP, Tailcat | Missing | Assess separately. Native management UI and local hardware view are applicable; captures, MCP, and Tailcat require explicit product-scope decisions |
| Embedding, rerank, image, speech, transcription, ComfyUI, SDAPI routes | Inapplicable today where FreeToken has no matching server route | Document absent FreeToken backend capability and reject safely. Do not mimic endpoint success |
| Accounting, drain/abort barrier, rollback | Native and more specific than direct llama-swap mode | Integrate into automatic routing, including loader failure and recovery tests |

## Native real-process gate

`tests/daemon/test_real_process_recovery.py` now includes a Linux-only native
router test that starts a disposable HTTP child through `ServeManager`, waits
for real `/health` readiness, routes an SSE request through the daemon, then
stops the child and verifies pidfile cleanup. It compiles and is skipped on
Windows. It has not yet been executed on a Linux host, so it is a pending gate,
not evidence of Linux completion.

## Architecture gate

The target is one FreeToken-owned router and lifecycle supervisor. It must not
delegate automatic routing to llama-swap while retaining safety only in the
manual daemon. The existing llama-swap integration remains a compatibility and
comparison reference until native request routing reaches the acceptance gates.

## Initial implementation sequence

1. Define a versioned router configuration and strict parser, including models,
   API keys, TTL, routing groups, priorities, and safe defaults.
2. Add a request-preserving native proxy with model selection, priority-aware
   FIFO admission, SSE forwarding, cancellation, and an observable running-state registry.
   The first implementation is present in `daemon/router.py` and
   `daemon/inference_proxy.py`; it is not yet live-qualified.
3. Connect proxy decisions to the existing `ServeManager` accounting, recovery,
   re-adoption, readiness, and process identity safeguards.
4. Add unload, profile, log, metrics, and configuration-reload management APIs.
5. Add group and capacity policies after single-model correctness, then qualify
   all concurrent residency on measured GMKtek EVO-X2 capacity.

Every row moves to Native only after deterministic tests and relevant live
evidence are linked here. No endpoint name alone establishes parity.
