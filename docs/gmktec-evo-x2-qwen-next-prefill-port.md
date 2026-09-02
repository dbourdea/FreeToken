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

## Corrected local llama.cpp and FreeToken finding

The local llama.cpp ROCm reference contains an RDNA4 matrix-quantized MMQ
family for Q4_K and Q5_K. Its dispatcher selects the quantized matrix path for
multi-token work and accepts an expert-id tensor for routed operations. The
reference has architecture-specific Q4_K and Q5_K RDNA4 configurations in
`ggml/src/ggml-cuda/mmq-config-rdna4.cuh` and launches the MMQ route from
`ggml/src/ggml-cuda/ggml-cuda.cu` when its selector accepts the matrix shape.

FreeToken also already contains the relevant routed matrix implementation:
`python/freetoken/kernel/csrc/gguf/moe.cuh` consumes sorted token ids, expert
ids, and padded expert-group boundaries through `ggml_moe_a8`. The Qwen helper
`_grouped_moe_a8` calls that implementation when grouped prefill is requested.
The previously tested grouped Q4_K and Q5_K candidates therefore exercised the
same broad matrix-style family and were rejected at the exact deterministic
quality gate. A second port of the same family would duplicate a failed test,
not create a new candidate.

The remaining implementation question is narrower: identify which difference
between the grouped matrix route and the qualified vector route changes the
model-visible result. Candidate sources include route ordering, token padding,
Q8_1 activation quantization/scatter, FP32 reduction order, or the temporary
BF16 conversion boundary. No throughput claim is valid until that difference
is isolated and exact equality is recovered.

## Corrected candidate boundary

The candidate must be a diagnostic, opt-in HIP-only isolation of one of the
matrix-route numerical boundaries above. It must preserve all of the following:

1. Original Q4_K, Q5_K, and exceptional Q6_K GGUF byte layouts.
2. Existing top-k router ordering, token sorting, expert ids, and output
   scatter order.
3. FP32 accumulation and the currently accepted visible-output quality
   fingerprint.
4. The existing vector route for decode and for any unsupported prompt shape.
5. Default-off behavior until the complete quality and serving gates pass.

This is not permission to substitute llama.cpp, change the model
quantization, alter sampling, or relax output equality. It is a narrowly
scoped repair investigation of an existing native FreeToken ROCm/HIP path.

C130 repeated the real-weight differential with every top-k route assigned to
one expert. Q4 gate/up still differed before SwiGLU, with 0.031250 maximum and
0.001667 mean absolute difference; Q5 down also differed when it received the
identical vector intermediate, with 0.002441 maximum and 0.000133 mean
absolute difference. The final routed result was not storage-equal. This rules
out mixed-expert sorting and cross-expert route order as the primary failure
class. The next diagnostic must compare the grouped tile representation and
matrix-dot scale and reduction sequence against the vector Q4_K and Q5_K dot
functions, one quantized block at a time, while retaining the vector output as
the exact reference.

C131 tested the first arithmetic repair: the grouped Q4_K and Q5_K min term
now recomputes the packed Q8_1 integer sum and applies the primary Q8 scale in
FP32, rather than consuming the precomputed rounded half-precision sum term.
The Q4 gate/up maximum difference fell from 0.031250 to 0.00390625 and its
mean difference fell to 0.0000000297. Q5 down with the identical vector
intermediate fell to 0.00024414 maximum and 0.00000000171 mean difference.
The output is still not storage-equal, so this candidate cannot enter API
quality or TPS testing. The next repair must preserve this Q8-sum correction
and isolate the remaining packed-dot or FP32 accumulation-order difference.

C133 added bounded residual coordinates. The remaining Q4 and Q5 differences
repeat over groups of eight routed rows at fixed output lanes. This rules out
token order, mixed-expert sorting, and scatter as residual causes. The next
candidate must operate inside the row-local grouped packed-dot path, either by
reconstructing the vector dot sequence from the tiled values or by proving and
repairing a remaining tile-layout discrepancy. It must retain the Q8-sum
correction and remain default-off until exact tensor equality is demonstrated.

C134 rebuilt the Q8-sum-repaired grouped path with four routed waves rather
than eight in a fresh isolated extension. Its single-expert real-weight
differential reproduced C131's Q4 gate/up, Q5 down, and final residual counts
and magnitudes exactly. The residual therefore does not originate from the
four-versus-eight routed-wave launch choice. The next diagnostic must compare
the common Q4_K and Q5_K tile-scale unpacking and the primary quantized-dot
sequence against the corresponding vector helpers, one packed block at a time.

C135 then tested the repaired grouped prefill route at the model level before
collecting any throughput result. The candidate reached a real OpenAI-compatible
completion but failed the canonical deterministic greedy AIME fingerprint:
`e10880eae5f5` rather than `3302eda43396`. The remaining sparse component
residual is therefore quality-significant, not merely a harmless tolerance
difference. The grouped route must remain default-off. The next repair must
achieve exact tensor equality or an independently verified equivalent
deterministic model output before it can enter any TPS comparison.

## Required implementation sequence

1. Build a component differential harness that runs the qualified vector path
   and the existing grouped matrix path on identical actual packed Qwen
   weights, routes, and activations, then locates the first divergent
   intermediate tensor.
2. Test one numerical boundary at a time: route order and scatter first, then
   Q8_1 activation quantization, then reduction and conversion boundaries.
3. Add a compile-time and environment-gated correction candidate that is
   mutually exclusive with the completed row-sharing flags.
4. Use actual first-layer Qwen packed weights,
   deterministic BF16 token batches, all 256 experts, and top-k eight routing.
5. Require byte-for-byte output equality with the accepted vector route before
   any service startup.
6. Run the existing exact API suite, cache-neutral long-prefix prefill test,
   scheduler test, concurrent C4 test, tail-latency test, and recovery proof.
7. Retain the candidate only if it preserves quality and improves the measured
   primary prefill result. Otherwise record the failure and leave it default
   off.

## Current state

C123 reached a terminal zero-swap failure after session 48. Sessions 1 through
47 had `runner_swap_kib=0`; session 48 preserved all three deterministic
visible answers but reported 128,376 KiB for the isolated Q4 process group.
The controller stopped the candidate and restored the normal Qwen service.

C124 completed the required per-process follow-up as an isolated 60-session,
minute-cadence diagnostic. All 60 deterministic three-turn conversations and
the postflight sample retained `runner_swap_kib=0`, including session 48 and
later sessions. Per-process telemetry recorded the HTTP parent, worker, and
helper memory states at every boundary, so a future recurrence is now directly
attributable. The first post-start request took 52.663 s and remains in the
all-sample summary; sessions 2 through 60 are separately reported as a
steady-state view with 414.83 ms maximum TTFT and 26.36 ms p99 token gap. The
controller restored the normal Qwen service to `status: ok` and
`maintenance: serving`, followed by a completed OpenAI-compatible
`RECOVERY_OK` response. C124 is an effective one-hour stability diagnostic,
not a substitute for the requested 24-hour qualification.

C126 completed the first real-weight grouped-versus-vector numerical
differential on layer zero with 1,024 deterministic BF16 activation rows,
256 experts, and top-k eight routing. The first observed mismatch is the Q4
gate/up projection before SwiGLU, with 0.031494 maximum absolute difference.
The Q5 down projection also differs from the vector path when it receives the
same vector intermediate, though its maximum difference is smaller at 0.003540.
The resulting final output differs, so neither projection may be promoted to an
API candidate. The next repair investigation must isolate how the grouped Q4
and Q5 kernels differ from the vector kernels in activation quantization,
route-index interpretation, and accumulation or conversion order. It must
preserve the established vector route as the reference and remain default-off
until exact equality is demonstrated.

C138 separately enabled the exact four-row vector treatment for Q5_K only.
The Q4_K and every other vector route remained on the qualified generic path.
Against a same-run generic-vector control, the Q5-only candidate reduced median
device time from 81.093 ms to 74.634 ms, a 7.97 percent improvement, while
preserving the real-weight output SHA-256 exactly and recording zero maximum
and mean absolute tensor difference. It is therefore distinct from the
non-identical grouped-matrix family and is eligible for the complete API gate.
The next execution must use the canonical deterministic quality fingerprint,
then measure cache-neutral prefill, scheduler, C4, TTFT, token-gap tails, and
protected-service recovery before considering default selection.
