# CuAsm SM120 CuInsFeeder notes

## Current layout

```
custom-sm120/
|-- CuInsFeeder/
|   |-- CuInsFeeder_test.py        # entry: iterate + trans for both samples (main guard)
|   |-- cublas_sm120_extract.py    # kept extraction script (sm_120 -> sm120_extract/); not run
|   |-- sm120_extract/             # existing bulk dumps, left in place untouched
|   |   |-- cublas.sass
|   |   `-- cublas_lt.sass
|   |-- trans_output/              # generated *.sass.control (git-ignored)
|   |-- .gitignore                 # sm*_extract/, trans_output/
|   `-- NOTES.md
`-- sass/                          # isolated fixtures (not ignored)
    |-- isolated_hmma_kernel_1.sass
    `-- isolated_imma_kernel_1.sass
```

## Fixture provenance

The two isolated samples were cut verbatim (byte ranges) from the existing
text dumps under `sm120_extract/`; no fresh library dump or cuobjdump run was
performed.

| fixture | source | byte range [start,end) | sha256 | instructions |
|---|---|---|---|---|
| `isolated_hmma_kernel_1.sass` | `sm120_extract/cublas.sass` | [686271222, 687715542) | `059a076f53a75239f057044df18d7924afe04f0fd50fd73c588af73e7f2bffe9` | 5512 |
| `isolated_imma_kernel_1.sass` | `sm120_extract/cublas_lt.sass` | [918781236, 923061404) | `b858b7fe1e39b9b0717ca1e7a11fa4e9e6f25ab6ee4d1b9e8e8cebd20faf8ef5` | 16336 |

- `isolated_hmma_kernel_1.sass`: function
  `_ZN7cutlass7Kernel2I67cutlass_80_tensorop_bf16_s16816gemm_bf16_grouped_128x64_64x3_align8EEvNT_6ParamsE`;
  its `.headerflags` line is `@"EF_CUDA_SM120 unrecognized:0"` and is preserved
  verbatim. First tensor op: `HMMA.16816.F32.BF16`.
- `isolated_imma_kernel_1.sass`: function `cublasLt_fused_imma_dgemm_splitk_kernel_sm80`.
  The `_sm80` suffix is part of the kernel name, not an arch selection - the
  ELF `.headerflags` is `EF_CUDA_SM120`. First tensor op: `IMMA.16832.S8.S8`.
