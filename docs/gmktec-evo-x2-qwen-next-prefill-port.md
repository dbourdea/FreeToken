# Next Qwen Q4 prefill port: routed MMQ on RDNA4

## Purpose

This note records the next untested, evidence-supported performance direction
for the native ROCm/HIP Qwen Q4 runner on the GMKtec EVO-X2. It is deliberately
not a performance claim, a production setting, or an instruction to enable a
new code path. Its purpose is to prevent the campaign from repeating completed
launch-shape, cache-copy, or Gated DeltaNet experiments.

## Evidence that closes earlier directions

The qualified C105 ROCprof prefill trace attributes the largest device-time
share to Q4_K and Q5_K routed-expert work. The campaign then tested two, three,
four, Q4-only four, and five output-row vector-sharing variants. Four rows is
the fastest exact component candidate, but it regresses the primary warm API
prefill metric. The whole row-sharing family is therefore closed unless a new
algorithm changes more than the number of adjacent output rows.

The same trace lists BF16 direct-copy and fused Gated DeltaNet work as
secondary costs. Earlier campaign controls already tested the fused mapped-host
expert-copy path and bounded Gated DeltaNet wave and pipeline-stage variants.
The copy path was byte-exact but slower at the API boundary. The Gated DeltaNet
component gain did not survive the complete serving gate. Dense Q8_0 and Q6_K
multi-wave candidates were also screened and rejected before API promotion.

## Local llama.cpp reference finding

The local llama.cpp ROCm reference contains an RDNA4 matrix-quantized MMQ
family for Q4_K and Q5_K. Its dispatcher selects the quantized matrix path for
multi-token work and accepts an expert-id tensor for routed operations. The
reference has architecture-specific Q4_K and Q5_K RDNA4 configurations in
`ggml/src/ggml-cuda/mmq-config-rdna4.cuh` and launches the MMQ route from
`ggml/src/ggml-cuda/ggml-cuda.cu` when its selector accepts the matrix shape.

FreeToken already vendors generic Q4_K and Q5_K MMQ building blocks in
`python/freetoken/kernel/csrc/gguf/mmq.cuh`. However, the Qwen routed-expert
prefill binding in `gguf_kernel.cu` calls the separate `moe.cuh` vector-family
entry point. That route uses the campaign's row-sharing variants, rather than
the RDNA4 matrix-quantized expert-id path. This difference is the remaining
high-value architectural gap between the two local implementations.

## Candidate boundary

The candidate must add an opt-in HIP-only routed-MMQ implementation for Q4_K
gate and up projections and Q5_K down projections when prompt length is at
least the declared matrix threshold. It must preserve all of the following:

1. Original Q4_K, Q5_K, and exceptional Q6_K GGUF byte layouts.
2. Existing top-k router ordering, token sorting, expert ids, and output
   scatter order.
3. FP32 accumulation and the currently accepted visible-output quality
   fingerprint.
4. The existing vector route for decode and for any unsupported prompt shape.
5. Default-off behavior until the complete quality and serving gates pass.

This is not permission to substitute llama.cpp, change the model
quantization, alter sampling, or relax output equality. It is a narrowly
scoped port of a locally inspected algorithmic family into the existing native
FreeToken ROCm/HIP runtime.

## Required implementation sequence

1. Extract only the routed MMQ dispatcher, Q4_K and Q5_K RDNA4 tile policy,
   and expert-id indexing behavior relevant to Qwen's 512-wide experts.
2. Add a compile-time and environment-gated candidate that is mutually
   exclusive with the completed row-sharing flags.
3. Add a component benchmark using actual first-layer Qwen packed weights,
   deterministic BF16 token batches, all 256 experts, and top-k eight routing.
4. Require byte-for-byte output equality with the accepted vector route before
   any service startup.
5. Run the existing exact API suite, cache-neutral long-prefix prefill test,
   scheduler test, concurrent C4 test, tail-latency test, and recovery proof.
6. Retain the candidate only if it preserves quality and improves the measured
   primary prefill result. Otherwise record the failure and leave it default
   off.

## Current state

The 24-hour isolated Q4 endurance controller is active. No candidate code may
be tested against its GPU process or its protected service until that controller
has reached a terminal state and recovery has been independently verified.
