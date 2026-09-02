// copied from
// https://github.com/vllm-project/vllm/blob/4492e3a55428e161ca8db381edc28263e5da4c8d/csrc/quantization/gguf/moe_vec.cuh
// copied and adapted from
// https://github.com/ggerganov/llama.cpp/blob/b2899/ggml-cuda/mmvq.cu
template <typename scalar_t, int qk, int qi, typename block_q_t, int vdr, vec_dot_q_cuda_t vec_dot_q_cuda>
static __global__ void moe_vec_q(
    const void* __restrict__ vx,
    const void* __restrict__ vy,
    scalar_t* __restrict__ dst,
    const int* topk_ids,
    const int topk,
    const int ncols,
    const int nrows,
    const int token_stride) {
  const auto row = blockIdx.x * blockDim.y + threadIdx.y;

  const auto token = blockIdx.z / topk;
  const auto expert = (topk_ids)[blockIdx.z];

  if (row >= nrows) {
    return;
  }

  const int blocks_per_row = ncols / qk;
  const int blocks_per_warp = vdr * WARP_SIZE / qi;

  // partial sum for each thread
  float tmp = 0.0f;

  const block_q_t* x = ((const block_q_t*)vx) + expert * nrows * blocks_per_row;
  const block_q8_1* y = (const block_q8_1*)(((const int*)vy) + token * token_stride);

  for (auto i = threadIdx.x / (qi / vdr); i < blocks_per_row; i += blocks_per_warp) {
    const int ibx = row * blocks_per_row + i;  // x block index

    const int iby = i * (qk / QK8_1);  // y block index that aligns with ibx

    const int iqs = vdr * (threadIdx.x % (qi / vdr));  // x block quant index when casting the quants to int

    tmp += vec_dot_q_cuda(&x[ibx], &y[iby], iqs);
  }

  // sum up partial sums and write back result
#pragma unroll
  for (int mask = WARP_SIZE / 2; mask > 0; mask >>= 1) {
    tmp += SGLANG_SHFL_XOR_SYNC(uint32_t(-1), tmp, mask);
  }

  if (threadIdx.x == 0) {
    dst[blockIdx.z * nrows + row] = tmp;
  }
}

#if defined(USE_ROCM)
#ifndef FREETOKEN_GGUF_MOE_K_TWO_ROWS_MIN_BLOCKS
#define FREETOKEN_GGUF_MOE_K_TWO_ROWS_MIN_BLOCKS 1
#endif
#ifndef FREETOKEN_GGUF_Q4_K_TWO_ROWS_MIN_BLOCKS
#define FREETOKEN_GGUF_Q4_K_TWO_ROWS_MIN_BLOCKS FREETOKEN_GGUF_MOE_K_TWO_ROWS_MIN_BLOCKS
#endif
#ifndef FREETOKEN_GGUF_Q5_K_TWO_ROWS_MIN_BLOCKS
#define FREETOKEN_GGUF_Q5_K_TWO_ROWS_MIN_BLOCKS FREETOKEN_GGUF_MOE_K_TWO_ROWS_MIN_BLOCKS
#endif

// Return whether the isolated Q4_K/Q5_K two-row candidate is enabled.  This
// is deliberately a runtime opt-in, not a build-wide default: production
// remains on the established generic vector kernel until this candidate has
// passed real-weight numerical, quality, and end-to-end timing gates.
static bool freetoken_moe_k_two_rows_enabled() {
  const char* value = std::getenv("FREETOKEN_GGUF_MOE_K_TWO_ROWS");
  return value != nullptr && (std::strcmp(value, "1") == 0 || std::strcmp(value, "true") == 0);
}

// Return whether the isolated three-row experiment is enabled.  This remains
// distinct from the qualified two-row flag so neither component screens nor
// normal API processes can accidentally select a higher-register candidate.
static bool freetoken_moe_k_three_rows_enabled() {
  const char* value = std::getenv("FREETOKEN_GGUF_MOE_K_THREE_ROWS");
  return value != nullptr && (std::strcmp(value, "1") == 0 || std::strcmp(value, "true") == 0);
}

// Return whether the isolated four-row experiment is enabled.  This is kept
// separate from the lower-row candidates because four live accumulators can
// change register pressure and occupancy even though it preserves the exact
// per-row arithmetic sequence.  Normal serving never selects it by default.
static bool freetoken_moe_k_env_enabled(const char* value) {
  return value != nullptr && (std::strcmp(value, "1") == 0 || std::strcmp(value, "true") == 0);
}

static bool freetoken_moe_k_four_rows_enabled() {
  return freetoken_moe_k_env_enabled(std::getenv("FREETOKEN_GGUF_MOE_K_FOUR_ROWS"));
}

// Five rows is the next bounded launch-geometry screen after the four-row
// candidate. It stays opt-in because five accumulators can change occupancy
// on gfx1151 even though the per-row arithmetic remains unchanged.
static bool freetoken_moe_k_five_rows_enabled() {
  return freetoken_moe_k_env_enabled(std::getenv("FREETOKEN_GGUF_MOE_K_FIVE_ROWS"));
}

// Allow the component and API gates to apply four-row sharing to Q4_K alone.
// The optional format-specific value takes precedence, including explicit zero,
// so a clean benchmark cannot inherit an unrelated parent-process setting.
static bool freetoken_q4_k_four_rows_enabled() {
  const char* value = std::getenv("FREETOKEN_GGUF_Q4_K_FOUR_ROWS");
  return value == nullptr ? freetoken_moe_k_four_rows_enabled() : freetoken_moe_k_env_enabled(value);
}

// Q5_K follows the global candidate unless an isolated gate explicitly selects
// a format-specific value. This mirrors the Q4_K control and keeps the two
// independent projections auditable in every generated artifact.
static bool freetoken_q5_k_four_rows_enabled() {
  const char* value = std::getenv("FREETOKEN_GGUF_Q5_K_FOUR_ROWS");
  return value == nullptr ? freetoken_moe_k_four_rows_enabled() : freetoken_moe_k_env_enabled(value);
}

// The HIP launcher is defined after the CUDA-compatible wrapper so the
// generic wrappers remain grouped by quantization format below.
template <typename scalar_t>
static void moe_vec_q4_0_q8_1_hip_two_rows_cuda(
    const void* vx,
    const void* vy,
    scalar_t* dst,
    const int* topk_ids,
    const int top_k,
    const int tokens,
    const int ncols,
    const int nrows,
    const int token_stride,
    cudaStream_t stream);

// Q4_K and Q5_K use the same per-row lane ownership as the generic vector
// kernel.  The candidate merely computes two adjacent output rows in one wave
// and retains a separate, identically ordered reduction for each row.  It
// therefore shares packed activations and route metadata without changing
// either row's quantized vector-dot implementation or output addressing.
template <typename scalar_t, int qi, typename block_q_t, int vdr, vec_dot_q_cuda_t vec_dot, int min_blocks>
// The default reserves one wave-sized block per compute unit. An isolated
// compile-time occupancy experiment may request two blocks, but it cannot
// alter results because the body below preserves every row's original lane
// reduction and vector-dot order.
__launch_bounds__(WARP_SIZE, min_blocks)
static __global__ void moe_vec_q_k_hip_two_rows(
    const void* __restrict__ vx,
    const void* __restrict__ vy,
    scalar_t* __restrict__ dst,
    const int* __restrict__ topk_ids,
    const int topk,
    const int ncols,
    const int nrows,
    const int token_stride) {
  const int row0 = 2 * blockIdx.x;
  const int route = blockIdx.y;
  if (row0 >= nrows) {
    return;
  }

  const int token = route / topk;
  const int expert = topk_ids[route];
  const int blocks_per_row = ncols / QK_K;
  const int blocks_per_wave = vdr * WARP_SIZE / qi;
  const block_q_t* x = ((const block_q_t*)vx) + expert * nrows * blocks_per_row;
  const block_q8_1* y = (const block_q8_1*)(((const int*)vy) + token * token_stride);
  float tmp0 = 0.0f;
  float tmp1 = 0.0f;

  for (int i = threadIdx.x / (qi / vdr); i < blocks_per_row; i += blocks_per_wave) {
    const int iby = i * (QK_K / QK8_1);
    const int iqs = vdr * (threadIdx.x % (qi / vdr));
    tmp0 += vec_dot(&x[row0 * blocks_per_row + i], &y[iby], iqs);
    if (row0 + 1 < nrows) {
      tmp1 += vec_dot(&x[(row0 + 1) * blocks_per_row + i], &y[iby], iqs);
    }
  }

#pragma unroll
  for (int mask = WARP_SIZE / 2; mask > 0; mask >>= 1) {
    tmp0 += SGLANG_SHFL_XOR_SYNC(uint32_t(-1), tmp0, mask);
    tmp1 += SGLANG_SHFL_XOR_SYNC(uint32_t(-1), tmp1, mask);
  }
  if (threadIdx.x == 0) {
    dst[route * nrows + row0] = tmp0;
  }
  if (threadIdx.x == 1 && row0 + 1 < nrows) {
    dst[route * nrows + row0 + 1] = tmp1;
  }
}

template <typename scalar_t, int qi, typename block_q_t, int vdr, vec_dot_q_cuda_t vec_dot, int min_blocks>
static void moe_vec_q_k_hip_two_rows_cuda(
    const void* vx,
    const void* vy,
    scalar_t* dst,
    const int* topk_ids,
    const int top_k,
    const int tokens,
    const int ncols,
    const int nrows,
    const int token_stride,
    cudaStream_t stream) {
  const dim3 block_nums((nrows + 1) / 2, tokens * top_k, 1);
  const dim3 block_dims(WARP_SIZE, 1, 1);
  moe_vec_q_k_hip_two_rows<scalar_t, qi, block_q_t, vdr, vec_dot, min_blocks>
      <<<block_nums, block_dims, 0, stream>>>(vx, vy, dst, topk_ids, top_k, ncols, nrows, token_stride);
}

// The three-row candidate extends the two-row mapping by assigning three
// adjacent output rows to one wave.  Each accumulator retains the production
// vector-dot call order, lane ownership, XOR reduction order, and destination
// address for its row.  Only the amount of work carried by the wave changes.
template <typename scalar_t, int qi, typename block_q_t, int vdr, vec_dot_q_cuda_t vec_dot, int min_blocks>
__launch_bounds__(WARP_SIZE, min_blocks)
static __global__ void moe_vec_q_k_hip_three_rows(
    const void* __restrict__ vx,
    const void* __restrict__ vy,
    scalar_t* __restrict__ dst,
    const int* __restrict__ topk_ids,
    const int topk,
    const int ncols,
    const int nrows,
    const int token_stride) {
  const int row0 = 3 * blockIdx.x;
  const int route = blockIdx.y;
  if (row0 >= nrows) {
    return;
  }

  const int token = route / topk;
  const int expert = topk_ids[route];
  const int blocks_per_row = ncols / QK_K;
  const int blocks_per_wave = vdr * WARP_SIZE / qi;
  const block_q_t* x = ((const block_q_t*)vx) + expert * nrows * blocks_per_row;
  const block_q8_1* y = (const block_q8_1*)(((const int*)vy) + token * token_stride);
  float tmp0 = 0.0f;
  float tmp1 = 0.0f;
  float tmp2 = 0.0f;

  for (int i = threadIdx.x / (qi / vdr); i < blocks_per_row; i += blocks_per_wave) {
    const int iby = i * (QK_K / QK8_1);
    const int iqs = vdr * (threadIdx.x % (qi / vdr));
    tmp0 += vec_dot(&x[row0 * blocks_per_row + i], &y[iby], iqs);
    if (row0 + 1 < nrows) {
      tmp1 += vec_dot(&x[(row0 + 1) * blocks_per_row + i], &y[iby], iqs);
    }
    if (row0 + 2 < nrows) {
      tmp2 += vec_dot(&x[(row0 + 2) * blocks_per_row + i], &y[iby], iqs);
    }
  }

#pragma unroll
  for (int mask = WARP_SIZE / 2; mask > 0; mask >>= 1) {
    tmp0 += SGLANG_SHFL_XOR_SYNC(uint32_t(-1), tmp0, mask);
    tmp1 += SGLANG_SHFL_XOR_SYNC(uint32_t(-1), tmp1, mask);
    tmp2 += SGLANG_SHFL_XOR_SYNC(uint32_t(-1), tmp2, mask);
  }
  if (threadIdx.x == 0) {
    dst[route * nrows + row0] = tmp0;
  }
  if (threadIdx.x == 1 && row0 + 1 < nrows) {
    dst[route * nrows + row0 + 1] = tmp1;
  }
  if (threadIdx.x == 2 && row0 + 2 < nrows) {
    dst[route * nrows + row0 + 2] = tmp2;
  }
}

template <typename scalar_t, int qi, typename block_q_t, int vdr, vec_dot_q_cuda_t vec_dot, int min_blocks>
static void moe_vec_q_k_hip_three_rows_cuda(
    const void* vx,
    const void* vy,
    scalar_t* dst,
    const int* topk_ids,
    const int top_k,
    const int tokens,
    const int ncols,
    const int nrows,
    const int token_stride,
    cudaStream_t stream) {
  const dim3 block_nums((nrows + 2) / 3, tokens * top_k, 1);
  const dim3 block_dims(WARP_SIZE, 1, 1);
  moe_vec_q_k_hip_three_rows<scalar_t, qi, block_q_t, vdr, vec_dot, min_blocks>
      <<<block_nums, block_dims, 0, stream>>>(vx, vy, dst, topk_ids, top_k, ncols, nrows, token_stride);
}

// The four-row candidate tests whether another adjacent output row can share
// the activation and routing loads efficiently on gfx1151.  Each accumulator
// performs the same vector-dot sequence and XOR tree as the generic kernel,
// so the candidate changes launch geometry only, not quantized arithmetic.
template <typename scalar_t, int qi, typename block_q_t, int vdr, vec_dot_q_cuda_t vec_dot, int min_blocks>
__launch_bounds__(WARP_SIZE, min_blocks)
static __global__ void moe_vec_q_k_hip_four_rows(
    const void* __restrict__ vx,
    const void* __restrict__ vy,
    scalar_t* __restrict__ dst,
    const int* __restrict__ topk_ids,
    const int topk,
    const int ncols,
    const int nrows,
    const int token_stride) {
  const int row0 = 4 * blockIdx.x;
  const int route = blockIdx.y;
  if (row0 >= nrows) {
    return;
  }

  const int token = route / topk;
  const int expert = topk_ids[route];
  const int blocks_per_row = ncols / QK_K;
  const int blocks_per_wave = vdr * WARP_SIZE / qi;
  const block_q_t* x = ((const block_q_t*)vx) + expert * nrows * blocks_per_row;
  const block_q8_1* y = (const block_q8_1*)(((const int*)vy) + token * token_stride);
  float tmp0 = 0.0f;
  float tmp1 = 0.0f;
  float tmp2 = 0.0f;
  float tmp3 = 0.0f;

  for (int i = threadIdx.x / (qi / vdr); i < blocks_per_row; i += blocks_per_wave) {
    const int iby = i * (QK_K / QK8_1);
    const int iqs = vdr * (threadIdx.x % (qi / vdr));
    tmp0 += vec_dot(&x[row0 * blocks_per_row + i], &y[iby], iqs);
    if (row0 + 1 < nrows) {
      tmp1 += vec_dot(&x[(row0 + 1) * blocks_per_row + i], &y[iby], iqs);
    }
    if (row0 + 2 < nrows) {
      tmp2 += vec_dot(&x[(row0 + 2) * blocks_per_row + i], &y[iby], iqs);
    }
    if (row0 + 3 < nrows) {
      tmp3 += vec_dot(&x[(row0 + 3) * blocks_per_row + i], &y[iby], iqs);
    }
  }

#pragma unroll
  for (int mask = WARP_SIZE / 2; mask > 0; mask >>= 1) {
    tmp0 += SGLANG_SHFL_XOR_SYNC(uint32_t(-1), tmp0, mask);
    tmp1 += SGLANG_SHFL_XOR_SYNC(uint32_t(-1), tmp1, mask);
    tmp2 += SGLANG_SHFL_XOR_SYNC(uint32_t(-1), tmp2, mask);
    tmp3 += SGLANG_SHFL_XOR_SYNC(uint32_t(-1), tmp3, mask);
  }
  if (threadIdx.x == 0) {
    dst[route * nrows + row0] = tmp0;
  }
  if (threadIdx.x == 1 && row0 + 1 < nrows) {
    dst[route * nrows + row0 + 1] = tmp1;
  }
  if (threadIdx.x == 2 && row0 + 2 < nrows) {
    dst[route * nrows + row0 + 2] = tmp2;
  }
  if (threadIdx.x == 3 && row0 + 3 < nrows) {
    dst[route * nrows + row0 + 3] = tmp3;
  }
}

// Launch the four-row candidate with one wave per output-row group and route.
// The grid rounds up so a final partial group remains correct for all shapes.
template <typename scalar_t, int qi, typename block_q_t, int vdr, vec_dot_q_cuda_t vec_dot, int min_blocks>
static void moe_vec_q_k_hip_four_rows_cuda(
    const void* vx,
    const void* vy,
    scalar_t* dst,
    const int* topk_ids,
    const int top_k,
    const int tokens,
    const int ncols,
    const int nrows,
    const int token_stride,
    cudaStream_t stream) {
  const dim3 block_nums((nrows + 3) / 4, tokens * top_k, 1);
  const dim3 block_dims(WARP_SIZE, 1, 1);
  moe_vec_q_k_hip_four_rows<scalar_t, qi, block_q_t, vdr, vec_dot, min_blocks>
      <<<block_nums, block_dims, 0, stream>>>(vx, vy, dst, topk_ids, top_k, ncols, nrows, token_stride);
}

// The five-row candidate shares activation and route loads across five output
// rows. Each accumulator uses the same vector-dot sequence and XOR reduction
// as the generic kernel, so this modifies launch geometry but not arithmetic.
template <typename scalar_t, int qi, typename block_q_t, int vdr, vec_dot_q_cuda_t vec_dot, int min_blocks>
__launch_bounds__(WARP_SIZE, min_blocks)
static __global__ void moe_vec_q_k_hip_five_rows(
    const void* __restrict__ vx,
    const void* __restrict__ vy,
    scalar_t* __restrict__ dst,
    const int* __restrict__ topk_ids,
    const int topk,
    const int ncols,
    const int nrows,
    const int token_stride) {
  const int row0 = 5 * blockIdx.x;
  const int route = blockIdx.y;
  if (row0 >= nrows) return;
  const int token = route / topk;
  const int expert = topk_ids[route];
  const int blocks_per_row = ncols / QK_K;
  const int blocks_per_wave = vdr * WARP_SIZE / qi;
  const block_q_t* x = ((const block_q_t*)vx) + expert * nrows * blocks_per_row;
  const block_q8_1* y = (const block_q8_1*)(((const int*)vy) + token * token_stride);
  float tmp0 = 0.0f, tmp1 = 0.0f, tmp2 = 0.0f, tmp3 = 0.0f, tmp4 = 0.0f;
  for (int i = threadIdx.x / (qi / vdr); i < blocks_per_row; i += blocks_per_wave) {
    const int iby = i * (QK_K / QK8_1);
    const int iqs = vdr * (threadIdx.x % (qi / vdr));
    tmp0 += vec_dot(&x[row0 * blocks_per_row + i], &y[iby], iqs);
    if (row0 + 1 < nrows) tmp1 += vec_dot(&x[(row0 + 1) * blocks_per_row + i], &y[iby], iqs);
    if (row0 + 2 < nrows) tmp2 += vec_dot(&x[(row0 + 2) * blocks_per_row + i], &y[iby], iqs);
    if (row0 + 3 < nrows) tmp3 += vec_dot(&x[(row0 + 3) * blocks_per_row + i], &y[iby], iqs);
    if (row0 + 4 < nrows) tmp4 += vec_dot(&x[(row0 + 4) * blocks_per_row + i], &y[iby], iqs);
  }
#pragma unroll
  for (int mask = WARP_SIZE / 2; mask > 0; mask >>= 1) {
    tmp0 += SGLANG_SHFL_XOR_SYNC(uint32_t(-1), tmp0, mask);
    tmp1 += SGLANG_SHFL_XOR_SYNC(uint32_t(-1), tmp1, mask);
    tmp2 += SGLANG_SHFL_XOR_SYNC(uint32_t(-1), tmp2, mask);
    tmp3 += SGLANG_SHFL_XOR_SYNC(uint32_t(-1), tmp3, mask);
    tmp4 += SGLANG_SHFL_XOR_SYNC(uint32_t(-1), tmp4, mask);
  }
  if (threadIdx.x == 0) dst[route * nrows + row0] = tmp0;
  if (threadIdx.x == 1 && row0 + 1 < nrows) dst[route * nrows + row0 + 1] = tmp1;
  if (threadIdx.x == 2 && row0 + 2 < nrows) dst[route * nrows + row0 + 2] = tmp2;
  if (threadIdx.x == 3 && row0 + 3 < nrows) dst[route * nrows + row0 + 3] = tmp3;
  if (threadIdx.x == 4 && row0 + 4 < nrows) dst[route * nrows + row0 + 4] = tmp4;
}

// Round the grid up so partial groups retain the generic kernel's bounds
// behavior. A wave still owns exactly one route and one output-row group.
template <typename scalar_t, int qi, typename block_q_t, int vdr, vec_dot_q_cuda_t vec_dot, int min_blocks>
static void moe_vec_q_k_hip_five_rows_cuda(
    const void* vx, const void* vy, scalar_t* dst, const int* topk_ids,
    const int top_k, const int tokens, const int ncols, const int nrows,
    const int token_stride, cudaStream_t stream) {
  const dim3 block_nums((nrows + 4) / 5, tokens * top_k, 1);
  const dim3 block_dims(WARP_SIZE, 1, 1);
  moe_vec_q_k_hip_five_rows<scalar_t, qi, block_q_t, vdr, vec_dot, min_blocks>
      <<<block_nums, block_dims, 0, stream>>>(vx, vy, dst, topk_ids, top_k, ncols, nrows, token_stride);
}
#endif

template <typename scalar_t>
static void moe_vec_q4_0_q8_1_cuda(
    const void* vx,
    const void* vy,
    scalar_t* dst,
    const int* topk_ids,
    const int top_k,
    const int tokens,
    const int ncols,
    const int nrows,
    const int token_stride,
    cudaStream_t stream) {
#if defined(USE_ROCM)
  // Route AMD builds through the one-wave/two-row specialization above.  CUDA
  // retains the established generic implementation until it has independent
  // NVIDIA evidence, so this HIP experiment cannot alter CUDA behavior.
  moe_vec_q4_0_q8_1_hip_two_rows_cuda<scalar_t>(
      vx, vy, dst, topk_ids, top_k, tokens, ncols, nrows, token_stride, stream);
#else
  const int block_num_y = (nrows + GGML_CUDA_MMV_Y - 1) / GGML_CUDA_MMV_Y;
  const dim3 block_nums(block_num_y, 1, tokens * top_k);
  const dim3 block_dims(WARP_SIZE, GGML_CUDA_MMV_Y, 1);
  moe_vec_q<scalar_t, QK4_0, QI4_0, block_q4_0, VDR_Q4_0_Q8_1_MMVQ, vec_dot_q4_0_q8_1>
      <<<block_nums, block_dims, 0, stream>>>(vx, vy, dst, topk_ids, top_k, ncols, nrows, token_stride);
#endif
}

#if defined(USE_ROCM)
// HIP Q4_0 MoE specialization derived from the current llama.cpp MMVQ row
// structure.  Unlike the older GGML_CUDA_MMV_Y=2 experiment, this launch uses
// one 32-lane wave for two rows, rather than two independent waves.  The two
// float accumulators share the same packed Q4_0 activation block and expert
// selection, reducing grid work while preserving FreeToken's existing packed
// bank layout, route indexing, and BF16 output contract.
template <typename scalar_t>
__launch_bounds__(WARP_SIZE, 1)
static __global__ void moe_vec_q4_0_hip_two_rows(
    const void* __restrict__ vx,
    const void* __restrict__ vy,
    scalar_t* __restrict__ dst,
    const int* __restrict__ topk_ids,
    const int topk,
    const int ncols,
    const int nrows,
    const int token_stride) {
  // X indexes adjacent pairs of output rows.  Y is the flattened
  // token/top-k route index, matching the former Z dimension exactly.
  const int row0 = 2 * blockIdx.x;
  const int route = blockIdx.y;
  if (row0 >= nrows) {
    return;
  }

  const int token = route / topk;
  const int expert = topk_ids[route];
  const int blocks_per_row = ncols / QK4_0;
  const int blocks_per_wave = VDR_Q4_0_Q8_1_MMVQ * WARP_SIZE / QI4_0;
  const block_q4_0* x = ((const block_q4_0*)vx) + expert * nrows * blocks_per_row;
  const block_q8_1* y = (const block_q8_1*)(((const int*)vy) + token * token_stride);

  // Each lane owns the same packed-Q4 range for both rows.  Keeping the
  // reductions separate preserves the original arithmetic for each result.
  float tmp0 = 0.0f;
  float tmp1 = 0.0f;
  for (int i = threadIdx.x / (QI4_0 / VDR_Q4_0_Q8_1_MMVQ); i < blocks_per_row;
       i += blocks_per_wave) {
    const int iby = i * (QK4_0 / QK8_1);
    const int iqs = VDR_Q4_0_Q8_1_MMVQ * (threadIdx.x % (QI4_0 / VDR_Q4_0_Q8_1_MMVQ));
    tmp0 += vec_dot_q4_0_q8_1(&x[row0 * blocks_per_row + i], &y[iby], iqs);
    if (row0 + 1 < nrows) {
      tmp1 += vec_dot_q4_0_q8_1(&x[(row0 + 1) * blocks_per_row + i], &y[iby], iqs);
    }
  }

  // A wave-level XOR reduction leaves the same sum in every lane.  Lane zero
  // writes row zero and lane one writes row one, avoiding shared memory.
#pragma unroll
  for (int mask = WARP_SIZE / 2; mask > 0; mask >>= 1) {
    tmp0 += SGLANG_SHFL_XOR_SYNC(uint32_t(-1), tmp0, mask);
    tmp1 += SGLANG_SHFL_XOR_SYNC(uint32_t(-1), tmp1, mask);
  }
  if (threadIdx.x == 0) {
    dst[route * nrows + row0] = tmp0;
  }
  if (threadIdx.x == 1 && row0 + 1 < nrows) {
    dst[route * nrows + row0 + 1] = tmp1;
  }
}

template <typename scalar_t>
static void moe_vec_q4_0_q8_1_hip_two_rows_cuda(
    const void* vx,
    const void* vy,
    scalar_t* dst,
    const int* topk_ids,
    const int top_k,
    const int tokens,
    const int ncols,
    const int nrows,
    const int token_stride,
    cudaStream_t stream) {
  // One block now covers two rows and one route.  ``tokens * top_k`` remains
  // the complete flattened routing domain used by the original launcher.
  const dim3 block_nums((nrows + 1) / 2, tokens * top_k, 1);
  const dim3 block_dims(WARP_SIZE, 1, 1);
  moe_vec_q4_0_hip_two_rows<scalar_t>
      <<<block_nums, block_dims, 0, stream>>>(vx, vy, dst, topk_ids, top_k, ncols, nrows, token_stride);
}
#endif

template <typename scalar_t>
static void moe_vec_q4_1_q8_1_cuda(
    const void* vx,
    const void* vy,
    scalar_t* dst,
    const int* topk_ids,
    const int top_k,
    const int tokens,
    const int ncols,
    const int nrows,
    const int token_stride,
    cudaStream_t stream) {
  const int block_num_y = (nrows + GGML_CUDA_MMV_Y - 1) / GGML_CUDA_MMV_Y;
  const dim3 block_nums(block_num_y, 1, tokens * top_k);
  const dim3 block_dims(WARP_SIZE, GGML_CUDA_MMV_Y, 1);
  moe_vec_q<scalar_t, QK4_0, QI4_1, block_q4_1, VDR_Q4_1_Q8_1_MMVQ, vec_dot_q4_1_q8_1>
      <<<block_nums, block_dims, 0, stream>>>(vx, vy, dst, topk_ids, top_k, ncols, nrows, token_stride);
}

template <typename scalar_t>
static void moe_vec_q5_0_q8_1_cuda(
    const void* vx,
    const void* vy,
    scalar_t* dst,
    const int* topk_ids,
    const int top_k,
    const int tokens,
    const int ncols,
    const int nrows,
    const int token_stride,
    cudaStream_t stream) {
  const int block_num_y = (nrows + GGML_CUDA_MMV_Y - 1) / GGML_CUDA_MMV_Y;
  const dim3 block_nums(block_num_y, 1, tokens * top_k);
  const dim3 block_dims(WARP_SIZE, GGML_CUDA_MMV_Y, 1);
  moe_vec_q<scalar_t, QK5_0, QI5_0, block_q5_0, VDR_Q5_0_Q8_1_MMVQ, vec_dot_q5_0_q8_1>
      <<<block_nums, block_dims, 0, stream>>>(vx, vy, dst, topk_ids, top_k, ncols, nrows, token_stride);
}

template <typename scalar_t>
static void moe_vec_q5_1_q8_1_cuda(
    const void* vx,
    const void* vy,
    scalar_t* dst,
    const int* topk_ids,
    const int top_k,
    const int tokens,
    const int ncols,
    const int nrows,
    const int token_stride,
    cudaStream_t stream) {
  const int block_num_y = (nrows + GGML_CUDA_MMV_Y - 1) / GGML_CUDA_MMV_Y;
  const dim3 block_nums(block_num_y, 1, tokens * top_k);
  const dim3 block_dims(WARP_SIZE, GGML_CUDA_MMV_Y, 1);
  moe_vec_q<scalar_t, QK5_1, QI5_1, block_q5_1, VDR_Q5_1_Q8_1_MMVQ, vec_dot_q5_1_q8_1>
      <<<block_nums, block_dims, 0, stream>>>(vx, vy, dst, topk_ids, top_k, ncols, nrows, token_stride);
}

template <typename scalar_t>
static void moe_vec_q8_0_q8_1_cuda(
    const void* vx,
    const void* vy,
    scalar_t* dst,
    const int* topk_ids,
    const int top_k,
    const int tokens,
    const int ncols,
    const int nrows,
    const int token_stride,
    cudaStream_t stream) {
  const int block_num_y = (nrows + GGML_CUDA_MMV_Y - 1) / GGML_CUDA_MMV_Y;
  const dim3 block_nums(block_num_y, 1, tokens * top_k);
  const dim3 block_dims(WARP_SIZE, GGML_CUDA_MMV_Y, 1);
  moe_vec_q<scalar_t, QK8_0, QI8_0, block_q8_0, VDR_Q8_0_Q8_1_MMVQ, vec_dot_q8_0_q8_1>
      <<<block_nums, block_dims, 0, stream>>>(vx, vy, dst, topk_ids, top_k, ncols, nrows, token_stride);
}

template <typename scalar_t>
static void moe_vec_q2_K_q8_1_cuda(
    const void* vx,
    const void* vy,
    scalar_t* dst,
    const int* topk_ids,
    const int top_k,
    const int tokens,
    const int ncols,
    const int nrows,
    const int token_stride,
    cudaStream_t stream) {
  const int block_num_y = (nrows + GGML_CUDA_MMV_Y - 1) / GGML_CUDA_MMV_Y;
  const dim3 block_nums(block_num_y, 1, tokens * top_k);
  const dim3 block_dims(WARP_SIZE, GGML_CUDA_MMV_Y, 1);
  moe_vec_q<scalar_t, QK_K, QI2_K, block_q2_K, VDR_Q2_K_Q8_1_MMVQ, vec_dot_q2_K_q8_1>
      <<<block_nums, block_dims, 0, stream>>>(vx, vy, dst, topk_ids, top_k, ncols, nrows, token_stride);
}

template <typename scalar_t>
static void moe_vec_q3_K_q8_1_cuda(
    const void* vx,
    const void* vy,
    scalar_t* dst,
    const int* topk_ids,
    const int top_k,
    const int tokens,
    const int ncols,
    const int nrows,
    const int token_stride,
    cudaStream_t stream) {
  const int block_num_y = (nrows + GGML_CUDA_MMV_Y - 1) / GGML_CUDA_MMV_Y;
  const dim3 block_nums(block_num_y, 1, tokens * top_k);
  const dim3 block_dims(WARP_SIZE, GGML_CUDA_MMV_Y, 1);
  moe_vec_q<scalar_t, QK_K, QI3_K, block_q3_K, VDR_Q3_K_Q8_1_MMVQ, vec_dot_q3_K_q8_1>
      <<<block_nums, block_dims, 0, stream>>>(vx, vy, dst, topk_ids, top_k, ncols, nrows, token_stride);
}

template <typename scalar_t>
static void moe_vec_q4_K_q8_1_cuda(
    const void* vx,
    const void* vy,
    scalar_t* dst,
    const int* topk_ids,
    const int top_k,
    const int tokens,
    const int ncols,
    const int nrows,
    const int token_stride,
    cudaStream_t stream) {
#if defined(USE_ROCM)
  if (freetoken_moe_k_five_rows_enabled()) {
    moe_vec_q_k_hip_five_rows_cuda<
        scalar_t, QI4_K, block_q4_K, VDR_Q4_K_Q8_1_MMVQ, vec_dot_q4_K_q8_1,
        FREETOKEN_GGUF_Q4_K_TWO_ROWS_MIN_BLOCKS>(
        vx, vy, dst, topk_ids, top_k, tokens, ncols, nrows, token_stride, stream);
    return;
  }
  if (freetoken_q4_k_four_rows_enabled()) {
    moe_vec_q_k_hip_four_rows_cuda<
        scalar_t, QI4_K, block_q4_K, VDR_Q4_K_Q8_1_MMVQ, vec_dot_q4_K_q8_1,
        FREETOKEN_GGUF_Q4_K_TWO_ROWS_MIN_BLOCKS>(
        vx, vy, dst, topk_ids, top_k, tokens, ncols, nrows, token_stride, stream);
    return;
  }
  if (freetoken_moe_k_three_rows_enabled()) {
    moe_vec_q_k_hip_three_rows_cuda<
        scalar_t, QI4_K, block_q4_K, VDR_Q4_K_Q8_1_MMVQ, vec_dot_q4_K_q8_1,
        FREETOKEN_GGUF_Q4_K_TWO_ROWS_MIN_BLOCKS>(
        vx, vy, dst, topk_ids, top_k, tokens, ncols, nrows, token_stride, stream);
    return;
  }
  if (freetoken_moe_k_two_rows_enabled()) {
    moe_vec_q_k_hip_two_rows_cuda<
        scalar_t, QI4_K, block_q4_K, VDR_Q4_K_Q8_1_MMVQ, vec_dot_q4_K_q8_1,
        FREETOKEN_GGUF_Q4_K_TWO_ROWS_MIN_BLOCKS>(
        vx, vy, dst, topk_ids, top_k, tokens, ncols, nrows, token_stride, stream);
    return;
  }
#endif
  const int block_num_y = (nrows + GGML_CUDA_MMV_Y - 1) / GGML_CUDA_MMV_Y;
  const dim3 block_nums(block_num_y, 1, tokens * top_k);
  const dim3 block_dims(WARP_SIZE, GGML_CUDA_MMV_Y, 1);
  moe_vec_q<scalar_t, QK_K, QI4_K, block_q4_K, VDR_Q4_K_Q8_1_MMVQ, vec_dot_q4_K_q8_1>
      <<<block_nums, block_dims, 0, stream>>>(vx, vy, dst, topk_ids, top_k, ncols, nrows, token_stride);
}

template <typename scalar_t>
static void moe_vec_q5_K_q8_1_cuda(
    const void* vx,
    const void* vy,
    scalar_t* dst,
    const int* topk_ids,
    const int top_k,
    const int tokens,
    const int ncols,
    const int nrows,
    const int token_stride,
    cudaStream_t stream) {
#if defined(USE_ROCM)
  if (freetoken_moe_k_five_rows_enabled()) {
    moe_vec_q_k_hip_five_rows_cuda<
        scalar_t, QI5_K, block_q5_K, VDR_Q5_K_Q8_1_MMVQ, vec_dot_q5_K_q8_1,
        FREETOKEN_GGUF_Q5_K_TWO_ROWS_MIN_BLOCKS>(
        vx, vy, dst, topk_ids, top_k, tokens, ncols, nrows, token_stride, stream);
    return;
  }
  if (freetoken_q5_k_four_rows_enabled()) {
    moe_vec_q_k_hip_four_rows_cuda<
        scalar_t, QI5_K, block_q5_K, VDR_Q5_K_Q8_1_MMVQ, vec_dot_q5_K_q8_1,
        FREETOKEN_GGUF_Q5_K_TWO_ROWS_MIN_BLOCKS>(
        vx, vy, dst, topk_ids, top_k, tokens, ncols, nrows, token_stride, stream);
    return;
  }
  if (freetoken_moe_k_three_rows_enabled()) {
    moe_vec_q_k_hip_three_rows_cuda<
        scalar_t, QI5_K, block_q5_K, VDR_Q5_K_Q8_1_MMVQ, vec_dot_q5_K_q8_1,
        FREETOKEN_GGUF_Q5_K_TWO_ROWS_MIN_BLOCKS>(
        vx, vy, dst, topk_ids, top_k, tokens, ncols, nrows, token_stride, stream);
    return;
  }
  if (freetoken_moe_k_two_rows_enabled()) {
    moe_vec_q_k_hip_two_rows_cuda<
        scalar_t, QI5_K, block_q5_K, VDR_Q5_K_Q8_1_MMVQ, vec_dot_q5_K_q8_1,
        FREETOKEN_GGUF_Q5_K_TWO_ROWS_MIN_BLOCKS>(
        vx, vy, dst, topk_ids, top_k, tokens, ncols, nrows, token_stride, stream);
    return;
  }
#endif
  const int block_num_y = (nrows + GGML_CUDA_MMV_Y - 1) / GGML_CUDA_MMV_Y;
  const dim3 block_nums(block_num_y, 1, tokens * top_k);
  const dim3 block_dims(WARP_SIZE, GGML_CUDA_MMV_Y, 1);
  moe_vec_q<scalar_t, QK_K, QI5_K, block_q5_K, VDR_Q5_K_Q8_1_MMVQ, vec_dot_q5_K_q8_1>
      <<<block_nums, block_dims, 0, stream>>>(vx, vy, dst, topk_ids, top_k, ncols, nrows, token_stride);
}

template <typename scalar_t>
static void moe_vec_q6_K_q8_1_cuda(
    const void* vx,
    const void* vy,
    scalar_t* dst,
    const int* topk_ids,
    const int top_k,
    const int tokens,
    const int ncols,
    const int nrows,
    const int token_stride,
    cudaStream_t stream) {
  const int block_num_y = (nrows + GGML_CUDA_MMV_Y - 1) / GGML_CUDA_MMV_Y;
  const dim3 block_nums(block_num_y, 1, tokens * top_k);
  const dim3 block_dims(WARP_SIZE, GGML_CUDA_MMV_Y, 1);
  moe_vec_q<scalar_t, QK_K, QI6_K, block_q6_K, VDR_Q6_K_Q8_1_MMVQ, vec_dot_q6_K_q8_1>
      <<<block_nums, block_dims, 0, stream>>>(vx, vy, dst, topk_ids, top_k, ncols, nrows, token_stride);
}

template <typename scalar_t>
static void moe_vec_iq2_xxs_q8_1_cuda(
    const void* vx,
    const void* vy,
    scalar_t* dst,
    const int* topk_ids,
    const int top_k,
    const int tokens,
    const int ncols,
    const int nrows,
    const int token_stride,
    cudaStream_t stream) {
  const int block_num_y = (nrows + GGML_CUDA_MMV_Y - 1) / GGML_CUDA_MMV_Y;
  const dim3 block_nums(block_num_y, 1, tokens * top_k);
  const dim3 block_dims(WARP_SIZE, GGML_CUDA_MMV_Y, 1);
  moe_vec_q<scalar_t, QK_K, QI2_XXS, block_iq2_xxs, 1, vec_dot_iq2_xxs_q8_1>
      <<<block_nums, block_dims, 0, stream>>>(vx, vy, dst, topk_ids, top_k, ncols, nrows, token_stride);
}

template <typename scalar_t>
static void moe_vec_iq2_xs_q8_1_cuda(
    const void* vx,
    const void* vy,
    scalar_t* dst,
    const int* topk_ids,
    const int top_k,
    const int tokens,
    const int ncols,
    const int nrows,
    const int token_stride,
    cudaStream_t stream) {
  const int block_num_y = (nrows + GGML_CUDA_MMV_Y - 1) / GGML_CUDA_MMV_Y;
  const dim3 block_nums(block_num_y, 1, tokens * top_k);
  const dim3 block_dims(WARP_SIZE, GGML_CUDA_MMV_Y, 1);
  moe_vec_q<scalar_t, QK_K, QI2_XS, block_iq2_xs, 1, vec_dot_iq2_xs_q8_1>
      <<<block_nums, block_dims, 0, stream>>>(vx, vy, dst, topk_ids, top_k, ncols, nrows, token_stride);
}

template <typename scalar_t>
static void moe_vec_iq2_s_q8_1_cuda(
    const void* vx,
    const void* vy,
    scalar_t* dst,
    const int* topk_ids,
    const int top_k,
    const int tokens,
    const int ncols,
    const int nrows,
    const int token_stride,
    cudaStream_t stream) {
  const int block_num_y = (nrows + GGML_CUDA_MMV_Y - 1) / GGML_CUDA_MMV_Y;
  const dim3 block_nums(block_num_y, 1, tokens * top_k);
  const dim3 block_dims(WARP_SIZE, GGML_CUDA_MMV_Y, 1);
  moe_vec_q<scalar_t, QK_K, QI2_S, block_iq2_s, 1, vec_dot_iq2_s_q8_1>
      <<<block_nums, block_dims, 0, stream>>>(vx, vy, dst, topk_ids, top_k, ncols, nrows, token_stride);
}

template <typename scalar_t>
static void moe_vec_iq3_xxs_q8_1_cuda(
    const void* vx,
    const void* vy,
    scalar_t* dst,
    const int* topk_ids,
    const int top_k,
    const int tokens,
    const int ncols,
    const int nrows,
    const int token_stride,
    cudaStream_t stream) {
  const int block_num_y = (nrows + GGML_CUDA_MMV_Y - 1) / GGML_CUDA_MMV_Y;
  const dim3 block_nums(block_num_y, 1, tokens * top_k);
  const dim3 block_dims(WARP_SIZE, GGML_CUDA_MMV_Y, 1);
  moe_vec_q<scalar_t, QK_K, QI3_XXS, block_iq3_xxs, 1, vec_dot_iq3_xxs_q8_1>
      <<<block_nums, block_dims, 0, stream>>>(vx, vy, dst, topk_ids, top_k, ncols, nrows, token_stride);
}

template <typename scalar_t>
static void moe_vec_iq1_s_q8_1_cuda(
    const void* vx,
    const void* vy,
    scalar_t* dst,
    const int* topk_ids,
    const int top_k,
    const int tokens,
    const int ncols,
    const int nrows,
    const int token_stride,
    cudaStream_t stream) {
  const int block_num_y = (nrows + GGML_CUDA_MMV_Y - 1) / GGML_CUDA_MMV_Y;
  const dim3 block_nums(block_num_y, 1, tokens * top_k);
  const dim3 block_dims(WARP_SIZE, GGML_CUDA_MMV_Y, 1);
  moe_vec_q<scalar_t, QK_K, QI1_S, block_iq1_s, 1, vec_dot_iq1_s_q8_1>
      <<<block_nums, block_dims, 0, stream>>>(vx, vy, dst, topk_ids, top_k, ncols, nrows, token_stride);
}

template <typename scalar_t>
static void moe_vec_iq1_m_q8_1_cuda(
    const void* vx,
    const void* vy,
    scalar_t* dst,
    const int* topk_ids,
    const int top_k,
    const int tokens,
    const int ncols,
    const int nrows,
    const int token_stride,
    cudaStream_t stream) {
  const int block_num_y = (nrows + GGML_CUDA_MMV_Y - 1) / GGML_CUDA_MMV_Y;
  const dim3 block_nums(block_num_y, 1, tokens * top_k);
  const dim3 block_dims(WARP_SIZE, GGML_CUDA_MMV_Y, 1);
  moe_vec_q<scalar_t, QK_K, QI1_M, block_iq1_m, 1, vec_dot_iq1_m_q8_1>
      <<<block_nums, block_dims, 0, stream>>>(vx, vy, dst, topk_ids, top_k, ncols, nrows, token_stride);
}

template <typename scalar_t>
static void moe_vec_iq4_nl_q8_1_cuda(
    const void* vx,
    const void* vy,
    scalar_t* dst,
    const int* topk_ids,
    const int top_k,
    const int tokens,
    const int ncols,
    const int nrows,
    const int token_stride,
    cudaStream_t stream) {
  const int block_num_y = (nrows + GGML_CUDA_MMV_Y - 1) / GGML_CUDA_MMV_Y;
  const dim3 block_nums(block_num_y, 1, tokens * top_k);
  const dim3 block_dims(WARP_SIZE, GGML_CUDA_MMV_Y, 1);
  moe_vec_q<scalar_t, QK4_NL, QI4_NL, block_iq4_nl, VDR_Q4_0_Q8_1_MMVQ, vec_dot_iq4_nl_q8_1>
      <<<block_nums, block_dims, 0, stream>>>(vx, vy, dst, topk_ids, top_k, ncols, nrows, token_stride);
}

template <typename scalar_t>
static void moe_vec_iq4_xs_q8_1_cuda(
    const void* vx,
    const void* vy,
    scalar_t* dst,
    const int* topk_ids,
    const int top_k,
    const int tokens,
    const int ncols,
    const int nrows,
    const int token_stride,
    cudaStream_t stream) {
  const int block_num_y = (nrows + GGML_CUDA_MMV_Y - 1) / GGML_CUDA_MMV_Y;
  const dim3 block_nums(block_num_y, 1, tokens * top_k);
  const dim3 block_dims(WARP_SIZE, GGML_CUDA_MMV_Y, 1);
  moe_vec_q<scalar_t, QK_K, QI4_XS, block_iq4_xs, 1, vec_dot_iq4_xs_q8_1>
      <<<block_nums, block_dims, 0, stream>>>(vx, vy, dst, topk_ids, top_k, ncols, nrows, token_stride);
}

template <typename scalar_t>
static void moe_vec_iq3_s_q8_1_cuda(
    const void* vx,
    const void* vy,
    scalar_t* dst,
    const int* topk_ids,
    const int top_k,
    const int tokens,
    const int ncols,
    const int nrows,
    const int token_stride,
    cudaStream_t stream) {
  const int block_num_y = (nrows + GGML_CUDA_MMV_Y - 1) / GGML_CUDA_MMV_Y;
  const dim3 block_nums(block_num_y, 1, tokens * top_k);
  const dim3 block_dims(WARP_SIZE, GGML_CUDA_MMV_Y, 1);
  moe_vec_q<scalar_t, QK_K, QI3_XS, block_iq3_s, 1, vec_dot_iq3_s_q8_1>
      <<<block_nums, block_dims, 0, stream>>>(vx, vy, dst, topk_ids, top_k, ncols, nrows, token_stride);
}
