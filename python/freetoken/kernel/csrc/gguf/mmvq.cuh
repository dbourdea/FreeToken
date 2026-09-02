// copied from
// https://github.com/vllm-project/vllm/blob/4492e3a55428e161ca8db381edc28263e5da4c8d/csrc/quantization/gguf/mmvq.cuh
// copied and adapted from https://github.com/ggerganov/llama.cpp/blob/b2899/ggml-cuda/mmvq.cu
#ifndef GGML_CUDA_Q8_MMV_WARPS
#define GGML_CUDA_Q8_MMV_WARPS 1
#endif

// The old vendored implementation assigns one physical wave to each Q8_0
// output row.  This Q8-only candidate follows modern llama.cpp's RDNA4
// direction: eight waves divide the K loop for one row, then wave zero reduces
// the partial sums.  Other GGUF types deliberately keep their accepted path.
template <typename scalar_t, int num_warps>
static __global__ void mul_mat_vec_q8_0_q8_1_warped(
    const void* __restrict__ vx,
    const void* __restrict__ vy,
    scalar_t* __restrict__ dst,
    const int ncols,
    const int nrows,
    const int nvecs) {
  const int row = blockIdx.x;
  const int vec = blockIdx.y;
  if (row >= nrows || vec >= nvecs) {
    return;
  }

  // The two-dimensional block has `num_warps` independent physical waves.
  // Each lane begins at a unique packed Q8 block and advances by their total
  // combined work stride, preserving the exact input and weight interpretation.
  const int lane = threadIdx.x;
  const int wave = threadIdx.y;
  const int thread = wave * WARP_SIZE + lane;
  const int blocks_per_row = ncols / QK8_0;
  const int blocks_per_iteration = VDR_Q8_0_Q8_1_MMVQ * num_warps * WARP_SIZE / QI8_0;
  const int nrows_y = (ncols + 512 - 1) / 512 * 512;
  const block_q8_0* x = static_cast<const block_q8_0*>(vx);
  const block_q8_1* y = static_cast<const block_q8_1*>(vy);
  float partial = 0.0f;

  for (int block = thread / (QI8_0 / VDR_Q8_0_Q8_1_MMVQ);
       block < blocks_per_row;
       block += blocks_per_iteration) {
    const int input_block = row * blocks_per_row + block;
    const int activation_block = vec * (nrows_y / QK8_1) + block * (QK8_0 / QK8_1);
    const int quant_index = VDR_Q8_0_Q8_1_MMVQ * (thread % (QI8_0 / VDR_Q8_0_Q8_1_MMVQ));
    partial += vec_dot_q8_0_q8_1(&x[input_block], &y[activation_block], quant_index);
  }

  // Only wave zero writes the result.  The other waves publish matching lane
  // partial sums to shared memory, allowing a deterministic lane-local merge
  // before the existing warp reduction produces the output scalar.
  __shared__ float wave_partials[num_warps - 1][WARP_SIZE];
  if (wave > 0) {
    wave_partials[wave - 1][lane] = partial;
  }
  __syncthreads();
  if (wave > 0) {
    return;
  }
#pragma unroll
  for (int index = 0; index < num_warps - 1; ++index) {
    partial += wave_partials[index][lane];
  }
#pragma unroll
  for (int mask = WARP_SIZE / 2; mask > 0; mask >>= 1) {
    partial += SGLANG_SHFL_XOR_SYNC(uint32_t(-1), partial, mask);
  }
  if (lane == 0) {
    dst[vec * nrows + row] = partial;
  }
}

template <typename scalar_t, int qk, int qi, typename block_q_t, int vdr, vec_dot_q_cuda_t vec_dot_q_cuda>
static __global__ void mul_mat_vec_q(
    const void* __restrict__ vx,
    const void* __restrict__ vy,
    scalar_t* __restrict__ dst,
    const int ncols,
    const int nrows,
    const int nvecs) {
  const auto row = blockIdx.x * blockDim.y + threadIdx.y;
  const auto vec = blockIdx.y;

  if (row >= nrows || vec >= nvecs) {
    return;
  }

  const int blocks_per_row = ncols / qk;
  const int blocks_per_warp = vdr * WARP_SIZE / qi;
  const int nrows_y = (ncols + 512 - 1) / 512 * 512;

  // partial sum for each thread
  float tmp = 0.0f;

  const block_q_t* x = (const block_q_t*)vx;
  const block_q8_1* y = (const block_q8_1*)vy;

  for (auto i = threadIdx.x / (qi / vdr); i < blocks_per_row; i += blocks_per_warp) {
    const int ibx = row * blocks_per_row + i;  // x block index

    const int iby = vec * (nrows_y / QK8_1) + i * (qk / QK8_1);  // y block index that aligns with ibx

    const int iqs = vdr * (threadIdx.x % (qi / vdr));  // x block quant index when casting the quants to int

    tmp += vec_dot_q_cuda(&x[ibx], &y[iby], iqs);
  }

  // sum up partial sums and write back result
#pragma unroll
  for (int mask = WARP_SIZE / 2; mask > 0; mask >>= 1) {
    tmp += SGLANG_SHFL_XOR_SYNC(uint32_t(-1), tmp, mask);
  }

  if (threadIdx.x == 0) {
    dst[vec * nrows + row] = tmp;
  }
}

template <typename scalar_t>
static void mul_mat_vec_q4_0_q8_1_cuda(
    const void* vx,
    const void* vy,
    scalar_t* dst,
    const int ncols,
    const int nrows,
    const int nvecs,
    cudaStream_t stream) {
  const int block_num_y = (nrows + GGML_CUDA_MMV_Y - 1) / GGML_CUDA_MMV_Y;
  const dim3 block_nums(block_num_y, nvecs, 1);
  const dim3 block_dims(WARP_SIZE, GGML_CUDA_MMV_Y, 1);
  mul_mat_vec_q<scalar_t, QK4_0, QI4_0, block_q4_0, VDR_Q4_0_Q8_1_MMVQ, vec_dot_q4_0_q8_1>
      <<<block_nums, block_dims, 0, stream>>>(vx, vy, dst, ncols, nrows, nvecs);
}

template <typename scalar_t>
static void mul_mat_vec_q4_1_q8_1_cuda(
    const void* vx,
    const void* vy,
    scalar_t* dst,
    const int ncols,
    const int nrows,
    const int nvecs,
    cudaStream_t stream) {
  const int block_num_y = (nrows + GGML_CUDA_MMV_Y - 1) / GGML_CUDA_MMV_Y;
  const dim3 block_nums(block_num_y, nvecs, 1);
  const dim3 block_dims(WARP_SIZE, GGML_CUDA_MMV_Y, 1);
  mul_mat_vec_q<scalar_t, QK4_0, QI4_1, block_q4_1, VDR_Q4_1_Q8_1_MMVQ, vec_dot_q4_1_q8_1>
      <<<block_nums, block_dims, 0, stream>>>(vx, vy, dst, ncols, nrows, nvecs);
}

template <typename scalar_t>
static void mul_mat_vec_q5_0_q8_1_cuda(
    const void* vx,
    const void* vy,
    scalar_t* dst,
    const int ncols,
    const int nrows,
    const int nvecs,
    cudaStream_t stream) {
  const int block_num_y = (nrows + GGML_CUDA_MMV_Y - 1) / GGML_CUDA_MMV_Y;
  const dim3 block_nums(block_num_y, nvecs, 1);
  const dim3 block_dims(WARP_SIZE, GGML_CUDA_MMV_Y, 1);
  mul_mat_vec_q<scalar_t, QK5_0, QI5_0, block_q5_0, VDR_Q5_0_Q8_1_MMVQ, vec_dot_q5_0_q8_1>
      <<<block_nums, block_dims, 0, stream>>>(vx, vy, dst, ncols, nrows, nvecs);
}

template <typename scalar_t>
static void mul_mat_vec_q5_1_q8_1_cuda(
    const void* vx,
    const void* vy,
    scalar_t* dst,
    const int ncols,
    const int nrows,
    const int nvecs,
    cudaStream_t stream) {
  const int block_num_y = (nrows + GGML_CUDA_MMV_Y - 1) / GGML_CUDA_MMV_Y;
  const dim3 block_nums(block_num_y, nvecs, 1);
  const dim3 block_dims(WARP_SIZE, GGML_CUDA_MMV_Y, 1);
  mul_mat_vec_q<scalar_t, QK5_1, QI5_1, block_q5_1, VDR_Q5_1_Q8_1_MMVQ, vec_dot_q5_1_q8_1>
      <<<block_nums, block_dims, 0, stream>>>(vx, vy, dst, ncols, nrows, nvecs);
}

template <typename scalar_t>
static void mul_mat_vec_q8_0_q8_1_cuda(
    const void* vx,
    const void* vy,
    scalar_t* dst,
    const int ncols,
    const int nrows,
    const int nvecs,
    cudaStream_t stream) {
#if GGML_CUDA_Q8_MMV_WARPS == 1
  const int block_num_y = (nrows + GGML_CUDA_MMV_Y - 1) / GGML_CUDA_MMV_Y;
  const dim3 block_nums(block_num_y, nvecs, 1);
  const dim3 block_dims(WARP_SIZE, GGML_CUDA_MMV_Y, 1);
  mul_mat_vec_q<scalar_t, QK8_0, QI8_0, block_q8_0, VDR_Q8_0_Q8_1_MMVQ, vec_dot_q8_0_q8_1>
      <<<block_nums, block_dims, 0, stream>>>(vx, vy, dst, ncols, nrows, nvecs);
#elif GGML_CUDA_Q8_MMV_WARPS == 8
  // One output row per block and eight waves per row match the selected modern
  // RDNA4 Q8_0 strategy while leaving every non-Q8 dispatch unchanged.
  const dim3 block_nums(nrows, nvecs, 1);
  const dim3 block_dims(WARP_SIZE, GGML_CUDA_Q8_MMV_WARPS, 1);
  mul_mat_vec_q8_0_q8_1_warped<scalar_t, GGML_CUDA_Q8_MMV_WARPS>
      <<<block_nums, block_dims, 0, stream>>>(vx, vy, dst, ncols, nrows, nvecs);
#else
#error "GGML_CUDA_Q8_MMV_WARPS must be 1 or 8"
#endif
}

template <typename scalar_t>
static void mul_mat_vec_q2_K_q8_1_cuda(
    const void* vx,
    const void* vy,
    scalar_t* dst,
    const int ncols,
    const int nrows,
    const int nvecs,
    cudaStream_t stream) {
  const int block_num_y = (nrows + GGML_CUDA_MMV_Y - 1) / GGML_CUDA_MMV_Y;
  const dim3 block_nums(block_num_y, nvecs, 1);
  const dim3 block_dims(WARP_SIZE, GGML_CUDA_MMV_Y, 1);
  mul_mat_vec_q<scalar_t, QK_K, QI2_K, block_q2_K, VDR_Q2_K_Q8_1_MMVQ, vec_dot_q2_K_q8_1>
      <<<block_nums, block_dims, 0, stream>>>(vx, vy, dst, ncols, nrows, nvecs);
}

template <typename scalar_t>
static void mul_mat_vec_q3_K_q8_1_cuda(
    const void* vx,
    const void* vy,
    scalar_t* dst,
    const int ncols,
    const int nrows,
    const int nvecs,
    cudaStream_t stream) {
  const int block_num_y = (nrows + GGML_CUDA_MMV_Y - 1) / GGML_CUDA_MMV_Y;
  const dim3 block_nums(block_num_y, nvecs, 1);
  const dim3 block_dims(WARP_SIZE, GGML_CUDA_MMV_Y, 1);
  mul_mat_vec_q<scalar_t, QK_K, QI3_K, block_q3_K, VDR_Q3_K_Q8_1_MMVQ, vec_dot_q3_K_q8_1>
      <<<block_nums, block_dims, 0, stream>>>(vx, vy, dst, ncols, nrows, nvecs);
}

template <typename scalar_t>
static void mul_mat_vec_q4_K_q8_1_cuda(
    const void* vx,
    const void* vy,
    scalar_t* dst,
    const int ncols,
    const int nrows,
    const int nvecs,
    cudaStream_t stream) {
  const int block_num_y = (nrows + GGML_CUDA_MMV_Y - 1) / GGML_CUDA_MMV_Y;
  const dim3 block_nums(block_num_y, nvecs, 1);
  const dim3 block_dims(WARP_SIZE, GGML_CUDA_MMV_Y, 1);
  mul_mat_vec_q<scalar_t, QK_K, QI4_K, block_q4_K, VDR_Q4_K_Q8_1_MMVQ, vec_dot_q4_K_q8_1>
      <<<block_nums, block_dims, 0, stream>>>(vx, vy, dst, ncols, nrows, nvecs);
}

template <typename scalar_t>
static void mul_mat_vec_q5_K_q8_1_cuda(
    const void* vx,
    const void* vy,
    scalar_t* dst,
    const int ncols,
    const int nrows,
    const int nvecs,
    cudaStream_t stream) {
  const int block_num_y = (nrows + GGML_CUDA_MMV_Y - 1) / GGML_CUDA_MMV_Y;
  const dim3 block_nums(block_num_y, nvecs, 1);
  const dim3 block_dims(WARP_SIZE, GGML_CUDA_MMV_Y, 1);
  mul_mat_vec_q<scalar_t, QK_K, QI5_K, block_q5_K, VDR_Q5_K_Q8_1_MMVQ, vec_dot_q5_K_q8_1>
      <<<block_nums, block_dims, 0, stream>>>(vx, vy, dst, ncols, nrows, nvecs);
}

template <typename scalar_t>
static void mul_mat_vec_q6_K_q8_1_cuda(
    const void* vx,
    const void* vy,
    scalar_t* dst,
    const int ncols,
    const int nrows,
    const int nvecs,
    cudaStream_t stream) {
  const int block_num_y = (nrows + GGML_CUDA_MMV_Y - 1) / GGML_CUDA_MMV_Y;
  const dim3 block_nums(block_num_y, nvecs, 1);
  const dim3 block_dims(WARP_SIZE, GGML_CUDA_MMV_Y, 1);
  mul_mat_vec_q<scalar_t, QK_K, QI6_K, block_q6_K, VDR_Q6_K_Q8_1_MMVQ, vec_dot_q6_K_q8_1>
      <<<block_nums, block_dims, 0, stream>>>(vx, vy, dst, ncols, nrows, nvecs);
}

template <typename scalar_t>
static void mul_mat_vec_iq2_xxs_q8_1_cuda(
    const void* vx,
    const void* vy,
    scalar_t* dst,
    const int ncols,
    const int nrows,
    const int nvecs,
    cudaStream_t stream) {
  const int block_num_y = (nrows + GGML_CUDA_MMV_Y - 1) / GGML_CUDA_MMV_Y;
  const dim3 block_nums(block_num_y, nvecs, 1);
  const dim3 block_dims(WARP_SIZE, GGML_CUDA_MMV_Y, 1);
  mul_mat_vec_q<scalar_t, QK_K, QI2_XXS, block_iq2_xxs, 1, vec_dot_iq2_xxs_q8_1>
      <<<block_nums, block_dims, 0, stream>>>(vx, vy, dst, ncols, nrows, nvecs);
}

template <typename scalar_t>
static void mul_mat_vec_iq2_xs_q8_1_cuda(
    const void* vx,
    const void* vy,
    scalar_t* dst,
    const int ncols,
    const int nrows,
    const int nvecs,
    cudaStream_t stream) {
  const int block_num_y = (nrows + GGML_CUDA_MMV_Y - 1) / GGML_CUDA_MMV_Y;
  const dim3 block_nums(block_num_y, nvecs, 1);
  const dim3 block_dims(WARP_SIZE, GGML_CUDA_MMV_Y, 1);
  mul_mat_vec_q<scalar_t, QK_K, QI2_XS, block_iq2_xs, 1, vec_dot_iq2_xs_q8_1>
      <<<block_nums, block_dims, 0, stream>>>(vx, vy, dst, ncols, nrows, nvecs);
}

template <typename scalar_t>
static void mul_mat_vec_iq2_s_q8_1_cuda(
    const void* vx,
    const void* vy,
    scalar_t* dst,
    const int ncols,
    const int nrows,
    const int nvecs,
    cudaStream_t stream) {
  const int block_num_y = (nrows + GGML_CUDA_MMV_Y - 1) / GGML_CUDA_MMV_Y;
  const dim3 block_nums(block_num_y, nvecs, 1);
  const dim3 block_dims(WARP_SIZE, GGML_CUDA_MMV_Y, 1);
  mul_mat_vec_q<scalar_t, QK_K, QI2_S, block_iq2_s, 1, vec_dot_iq2_s_q8_1>
      <<<block_nums, block_dims, 0, stream>>>(vx, vy, dst, ncols, nrows, nvecs);
}

template <typename scalar_t>
static void mul_mat_vec_iq3_xxs_q8_1_cuda(
    const void* vx,
    const void* vy,
    scalar_t* dst,
    const int ncols,
    const int nrows,
    const int nvecs,
    cudaStream_t stream) {
  const int block_num_y = (nrows + GGML_CUDA_MMV_Y - 1) / GGML_CUDA_MMV_Y;
  const dim3 block_nums(block_num_y, nvecs, 1);
  const dim3 block_dims(WARP_SIZE, GGML_CUDA_MMV_Y, 1);
  mul_mat_vec_q<scalar_t, QK_K, QI3_XXS, block_iq3_xxs, 1, vec_dot_iq3_xxs_q8_1>
      <<<block_nums, block_dims, 0, stream>>>(vx, vy, dst, ncols, nrows, nvecs);
}

template <typename scalar_t>
static void mul_mat_vec_iq1_s_q8_1_cuda(
    const void* vx,
    const void* vy,
    scalar_t* dst,
    const int ncols,
    const int nrows,
    const int nvecs,
    cudaStream_t stream) {
  const int block_num_y = (nrows + GGML_CUDA_MMV_Y - 1) / GGML_CUDA_MMV_Y;
  const dim3 block_nums(block_num_y, nvecs, 1);
  const dim3 block_dims(WARP_SIZE, GGML_CUDA_MMV_Y, 1);
  mul_mat_vec_q<scalar_t, QK_K, QI1_S, block_iq1_s, 1, vec_dot_iq1_s_q8_1>
      <<<block_nums, block_dims, 0, stream>>>(vx, vy, dst, ncols, nrows, nvecs);
}

template <typename scalar_t>
static void mul_mat_vec_iq1_m_q8_1_cuda(
    const void* vx,
    const void* vy,
    scalar_t* dst,
    const int ncols,
    const int nrows,
    const int nvecs,
    cudaStream_t stream) {
  const int block_num_y = (nrows + GGML_CUDA_MMV_Y - 1) / GGML_CUDA_MMV_Y;
  const dim3 block_nums(block_num_y, nvecs, 1);
  const dim3 block_dims(WARP_SIZE, GGML_CUDA_MMV_Y, 1);
  mul_mat_vec_q<scalar_t, QK_K, QI1_M, block_iq1_m, 1, vec_dot_iq1_m_q8_1>
      <<<block_nums, block_dims, 0, stream>>>(vx, vy, dst, ncols, nrows, nvecs);
}

template <typename scalar_t>
static void mul_mat_vec_iq4_nl_q8_1_cuda(
    const void* vx,
    const void* vy,
    scalar_t* dst,
    const int ncols,
    const int nrows,
    const int nvecs,
    cudaStream_t stream) {
  const int block_num_y = (nrows + GGML_CUDA_MMV_Y - 1) / GGML_CUDA_MMV_Y;
  const dim3 block_nums(block_num_y, nvecs, 1);
  const dim3 block_dims(WARP_SIZE, GGML_CUDA_MMV_Y, 1);
  mul_mat_vec_q<scalar_t, QK4_NL, QI4_NL, block_iq4_nl, VDR_Q4_0_Q8_1_MMVQ, vec_dot_iq4_nl_q8_1>
      <<<block_nums, block_dims, 0, stream>>>(vx, vy, dst, ncols, nrows, nvecs);
}

template <typename scalar_t>
static void mul_mat_vec_iq4_xs_q8_1_cuda(
    const void* vx,
    const void* vy,
    scalar_t* dst,
    const int ncols,
    const int nrows,
    const int nvecs,
    cudaStream_t stream) {
  const int block_num_y = (nrows + GGML_CUDA_MMV_Y - 1) / GGML_CUDA_MMV_Y;
  const dim3 block_nums(block_num_y, nvecs, 1);
  const dim3 block_dims(WARP_SIZE, GGML_CUDA_MMV_Y, 1);
  mul_mat_vec_q<scalar_t, QK_K, QI4_XS, block_iq4_xs, 1, vec_dot_iq4_xs_q8_1>
      <<<block_nums, block_dims, 0, stream>>>(vx, vy, dst, ncols, nrows, nvecs);
}

template <typename scalar_t>
static void mul_mat_vec_iq3_s_q8_1_cuda(
    const void* vx,
    const void* vy,
    scalar_t* dst,
    const int ncols,
    const int nrows,
    const int nvecs,
    cudaStream_t stream) {
  const int block_num_y = (nrows + GGML_CUDA_MMV_Y - 1) / GGML_CUDA_MMV_Y;
  const dim3 block_nums(block_num_y, nvecs, 1);
  const dim3 block_dims(WARP_SIZE, GGML_CUDA_MMV_Y, 1);
  mul_mat_vec_q<scalar_t, QK_K, QI3_XS, block_iq3_s, 1, vec_dot_iq3_s_q8_1>
      <<<block_nums, block_dims, 0, stream>>>(vx, vy, dst, ncols, nrows, nvecs);
}
