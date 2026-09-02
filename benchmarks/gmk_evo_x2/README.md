# GMKtec EVO-X2 Qwen API replication harness

`run_api_benchmark.py` measures a running local FreeToken server through its
OpenAI-compatible streaming API. It does not start a service, modify model
files, change llama-swap, or contact another LAN host. The script refuses to
run unless the operating system host name is GMKtec EVO-X2 or an explicitly supplied
test host.

Run a quality canary on GMKtec EVO-X2 from the isolated FreeToken environment after
the server is already warm:

```bash
python benchmarks/gmk_evo_x2/run_api_benchmark.py \
  --model qwen3.6-35b-a3b-nvfp4 \
  --tokenizer /home/david/freetoken-amd/models/Qwen3.6-35B-A3B-NVFP4 \
  --base-url http://127.0.0.1:1919/v1 \
  --samples 5 \
  --artifact-dir /home/david/freetoken-amd/artifacts/qwen-replication-$(date -u +%Y%m%dT%H%M%SZ)
```

For a fixed-length decode TPS measurement, pass the exact paper or surrogate
prompt and opt into throughput mode. This sends `ignore_eos=true` so all samples
produce the same requested decode length:

```bash
python benchmarks/gmk_evo_x2/run_api_benchmark.py \
  --model qwen3.6-35b-a3b-nvfp4 \
  --tokenizer /home/david/freetoken-amd/models/Qwen3.6-35B-A3B-NVFP4 \
  --base-url http://127.0.0.1:1919/v1 \
  --mode throughput --expected-text '' --max-tokens 256 \
  --prompt "<fixed benchmark prompt>" --samples 5 \
  --artifact-dir /home/david/freetoken-amd/artifacts/qwen-throughput-$(date -u +%Y%m%dT%H%M%SZ)
```

The harness writes one immutable JSON artifact per request plus a manifest and
summary. Decode TPS is based on tokenizer-counted generated text rather than
the count of network chunks. A server that fails to provide content, returns a
malformed SSE sequence, or emits an error is marked failed rather than silently
excluded.

Quality and fixed-length throughput are intentionally separate modes. The
harness is not a paper replication until the exact published prompt, sampling,
cache state, and statistic are supplied in the protocol artifact.
Each passed sample records both decode TPS and `client_prefill_tps`.  The latter
is prompt tokens divided by warm TTFT, so it represents the client-visible
request-to-first-text boundary.  It is intentionally reported separately from
any server log's internal input-throughput line, whose timing boundary differs.

The per-sample `timing` object also records an auditable API timing breakdown:
`response_headers_seconds`, `headers_to_first_text_seconds`,
`first_text_to_stream_close_seconds`, and `last_text_to_stream_close_seconds`.
These values identify client-observable request phases only.  They do not claim
to separate tokenization, queueing, scheduler execution, model prefill, or GPU
kernel work, which the OpenAI-compatible streaming API does not expose as
independent timestamped events.  ROCm profiler evidence remains the source for
kernel-level attribution.

## Grouped Q4 prefill numerical differential

`bench_qwen_q4_grouped_differential.py` is a component diagnostic for the
default-off grouped Q4_K and Q5_K matrix prefill path. It is not an API
benchmark and never reports its device work as request TPS. It materializes a
real Qwen expert layer, then compares the accepted vector implementation with
the grouped implementation at the Q4 gate/up, SwiGLU intermediate, Q5 down,
and final router-weighted output boundaries. The resulting JSON identifies the
first divergent tensor before any attempt to change the grouped path.

Run it only while no protected service or endurance controller owns the GPU:

```bash
python benchmarks/gmk_evo_x2/bench_qwen_q4_grouped_differential.py \
  --model /home/david/freetoken-amd/models/controls/qwen36-35b-a3b-unsloth-a483e9e6/Qwen3.6-35B-A3B-UD-Q4_K_M.gguf \
  --json /home/david/freetoken-amd/artifacts/q4-grouped-differential-$(date -u +%Y%m%dT%H%M%SZ).json
```

The command refuses to overwrite an existing artifact and requires a native
ROCm/HIP PyTorch device. A mismatch is expected evidence for this diagnostic,
not a test failure to hide or a reason to relax model-output quality checks.
