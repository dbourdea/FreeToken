# Qwen3.8 dense FreeToken and ROCm llama.cpp comparison

Date: 2026-09-04

Both controls used the same Qwen3.8 27B Q4_K_M GGUF, the same fixed prompt,
one warmup, five scored streaming requests, greedy sampling, and a 128-token
limit. The raw artifacts are preserved on the GMKtec EVO-X2.

| Metric | FreeToken dense AMD | llama.cpp ROCm 10 | Interpretation |
| --- | ---: | ---: | --- |
| Mean decode | 11.1702 TPS | 11.0726 TPS | FreeToken is 0.88% higher |
| Median decode | 11.1714 TPS | 11.0740 TPS | FreeToken is 0.88% higher |
| Mean TTFT | 653.39 ms | 191.58 ms | llama.cpp is 70.65% lower |
| Derived mean prefill | 48.71 TPS | 137.11 TPS | llama.cpp is 2.81x higher |
| Scored samples | 5 of 5 | 5 of 5 | No protocol failures |
| Prompt tokens | 26 each | 26 each | Same tokenizer and prompt |
| Completion tokens | 127 each | 127 each | Same output length |
| Maximum sample p99 token gap | 94.15 ms | 92.20 ms | llama.cpp is slightly lower |

FreeToken's decode result is effectively tied with the matching llama.cpp
control and is 0.88% higher in this workload. llama.cpp has materially better
first-token latency and prefill. Prefill is derived as prompt tokens divided by
TTFT because the client does not receive a separate server prefill timer.

FreeToken artifact:

`/home/david/freetoken-amd/artifacts/qwen35-dense-perf-20260904T210621Z/`

llama.cpp artifact:

`/home/david/freetoken-amd/artifacts/qwen38-llamacpp-rocm10-perf-20260904T211635Z/`

This is a practical same-format comparison. It is not a claim of strict
FreeToken-paper parity, and it is not an endurance result.
