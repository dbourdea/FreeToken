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
| Model catalog and aliases | Native TOML catalog with validated model, port, args, description, readiness timeout | Add YAML-compatible import or documented translation, atomic reload, tests for invalid and changed configuration |
| Start, stop, switch, PID identity, re-adoption | Native and tested | Preserve as router substrate; exercise automatic-request ownership |
| Readiness and diagnostic health | Native `/ready` plus diagnostic `/health` | Preserve exact HTTP behavior through the unified router |
| Automatic OpenAI model-ID routing | Native single-engine coordinator with priority-aware admission and health-gated activation | `tests/daemon/test_router.py` covers cold activation, same-model concurrent leases, safe swap waiting, and unknown-model errors. Linux and GMKtek EVO-X2 evidence remains required. |
| OpenAI completion and chat completion forwarding | Native request-byte-preserving proxy, including SSE body forwarding | Deterministic HTTP tests cover `/v1/chat/completions`; direct, cold, warm, cancellation, and performance evidence remains required. |
| OpenAI Responses endpoint | Native route uses the same admission and proxy contract | Add explicit cancellation and response-object lifecycle proof. |
| Anthropic Messages and token-count routing | Native routes use the same admission and proxy contract | Deterministic HTTP Messages test exists; add token-count and live failure proof. |
| Unknown-model status and direct upstream access | Integrated only | Native compatible error response and `/upstream/{model}/...` behavior |
| FIFO, priority, exclusive group routing | Integrated only | Native queue and group admission with deterministic tests |
| Matrix capacity policy and eviction costs | Integrated only | Native validated capacity policy, observable selection, memory-qualified live tests |
| Persistent resident models | Integrated only | Native capacity admission and protected persistent lifecycle tests |
| TTL and unload timeout | Integrated only | Native timer, explicit unload, process cleanup and accounting tests |
| Load/unload management API and running-model list | Partial native status/start/stop routes | Compatible configured/running, unload one/all endpoints and behavior tests |
| Profiles | Native named catalog profiles, different API | Native profile listing/activation compatibility policy and tests |
| API keys | Native daemon token, different header and scope | Router inference and management key policy with authorization tests |
| Logs and bounded streaming logs | Native engine log snapshot only | Bounded router/proxy/upstream log buffers and SSE log streams |
| Prometheus and activity/performance metrics | Native `/metrics` exposes bounded router admission, queue, activation, failure, and eviction counters; engine metrics remain separately available | Add TTFT, throughput, cancellation, process, and memory measurements with direct/cold/warm/alternating benchmark evidence. |
| Inflight cancellation API | Native backend cancellation on client disconnect | Router inflight identifiers and explicit cancel API, with same-instance terminal-abort proof |
| Parameter filters and configuration hooks | Missing | Safe allowlisted parameter transformation and lifecycle hooks, or explicit supported subset policy |
| Configuration watch/reload | Missing | Atomic validated reload without disrupting active routing |
| UI, hardware, captures, MCP, Tailcat | Missing | Assess separately. Native management UI and local hardware view are applicable; captures, MCP, and Tailcat require explicit product-scope decisions |
| Embedding, rerank, image, speech, transcription, ComfyUI, SDAPI routes | Inapplicable today where FreeToken has no matching server route | Document absent FreeToken backend capability and reject safely. Do not mimic endpoint success |
| Accounting, drain/abort barrier, rollback | Native and more specific than direct llama-swap mode | Integrate into automatic routing, including loader failure and recovery tests |

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
