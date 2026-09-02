# FreeToken Paper Protocol Disclosure and Replication Boundary

This record distinguishes facts disclosed by the supplied FreeToken paper from
inputs that are required for strict replication but are not published in that
paper. It prevents the AMD campaign from treating a similar local workload as
an identical paper result.

## Disclosed by the paper

The paper identifies the following evaluation facts:

- The 284B demonstration is DeepSeek-V4-Flash, described as 284B parameters
  with 13B active parameters and native MXFP4 routed experts.
- The 32 GB gaming desktop is an RTX 5090 desktop with a Ryzen 9 9950X3D,
  DDR5 192 GiB, PCIe 5.0 x16, measured host-to-device bandwidth of 49.0 GB/s,
  and measured CPU expert-kernel bandwidth of 53.8 GB/s.
- W1 is long-chain-of-thought AIME math reasoning without tools.
- W2 is one SWE-bench repository issue solved through OpenCode with real tools
  over three scripted user turns, and it must produce a reference gold patch.
- W3 is the same issue through Claude Code over an Anthropic-compatible API,
  with concurrently requesting subagents and 56K to 65K-token sessions.
- W4 is thirteen fixed OpenClaw mailbox and calendar turns with an approximate
  24.5K-token system-context floor. The default 120-second idle watchdog is
  disabled.
- The reported metrics are per-request mean decode throughput and per-request
  mean TTFT. The paper says cross-engine total wall time is not compared.

## Not disclosed and therefore unresolved

The paper does not disclose the following strict-replication inputs:

| Required item | Why it is necessary | Current campaign treatment |
| --- | --- | --- |
| Exact W1 AIME problem identifiers, prompts, template options, output limits, and expected answers | A different AIME sample or decode limit changes both quality and token timing | Local deterministic AIME controls only; no W1 parity claim |
| W2 SWE-bench repository, issue, checkout, OpenCode version, configuration, tool policy, three user turns, and reference patch | These define the actual coding-agent trajectory and gold-patch gate | Bounded sandbox tool-call and patch control only; no W2 parity claim |
| W3 Claude Code version, Anthropic request details, subagent policy, complete trace, compaction behavior, and gold patch | The stated 56K to 65K context growth and concurrency cannot be reconstructed from a summary | Not run; host test profile does not expose that context capacity |
| W4 OpenClaw version, mailbox kit, thirteen prompts, credentials or fixtures, configuration, and exact context template | The 24.5K floor and tool results determine each prefill and final task outcome | Not run; host test profile does not expose that context capacity |
| Per-workload raw timing samples, warmup policy, sample count, sampling parameters, cache state, and outlier handling | Means alone cannot establish an equivalent distribution or confidence interval | Local results retain raw artifacts and report their own protocol separately |
| Complete engine launch arguments and model checksums for every baseline cell | Exact runtime and weight parity cannot be inferred from architecture names alone | Local ROCm llama.cpp controls are labelled time-shared and format-specific |

## Consequence for this AMD campaign

The campaign can reproduce native API behavior, local quality gates, bounded
tool execution, long-context controls within the active profile, and ROCm
llama.cpp comparisons with retained raw artifacts. It cannot claim strict
paper W1 through W4 parity, direct NVIDIA superiority, or replication of the
284B demonstration unless the missing fixtures and configurations are supplied
and a suitably capable system is available.

The following are valid, narrower claims when their corresponding artifacts
pass: native ROCm/HIP function, OpenAI-compatible API behavior, quality on the
defined local suite, bounded tool-call behavior, local prefill and decode TPS,
and time-shared ROCm llama.cpp comparison under the documented model formats.
