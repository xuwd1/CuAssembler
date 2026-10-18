tcgen05 PTX kind -> SASS mapping, CUDA 13.4.92, ptxas -arch=sm_100a
probe.ptx: 9 entries, all assembled cleanly (ptxas.log empty, exit 0)
SASS operand order: MMA gdesc[A], gdesc[B], tmem[D], tmem[meta/sf slot], idesc[UR5], UPT

ENTRY          PTX form                                                        SASS
f16            tcgen05.mma.cta_group::1.kind::f16                               UTCHMMA gdesc[UR8], gdesc[UR10], tmem[UR6], tmem[UR4], idesc[UR5], UPT ;  enc 0x00ff040a080075ea / 0x01f9d8000b800006
tf32           tcgen05.mma.cta_group::1.kind::tf32                              UTCHMMA gdesc[UR8], gdesc[UR10], tmem[UR6], tmem[UR4], idesc[UR5], UPT ;  enc 0x00ff040a080075ea / 0x01f9d8000b800006  (byte-identical encoding to f16; dtype only in idesc)
f8f6f4         tcgen05.mma.cta_group::1.kind::f8f6f4                            UTCQMMA gdesc[UR8], gdesc[UR10], tmem[UR6], tmem[UR4], idesc[UR5], UPT ;  enc 0x00ff040a080075ea / 0x01f9d8000b800306
i8             tcgen05.mma.cta_group::1.kind::i8                                UTCIMMA gdesc[UR8], gdesc[UR10], tmem[UR6], tmem[UR4], idesc[UR5], UPT ;  enc 0x00ff040a080075ea / 0x01f9d8000b800106
mxf8f6f4       tcgen05.mma...kind::mxf8f6f4.block_scale.scale_vec::1X           UTCQMMA gdesc[UR12], gdesc[UR14], tmem[UR10], tmem[UR4], idesc[UR5], tmem[UR8], UPT ;  enc 0x0008040e0c007dea / 0x01e1f4000b80030a  (same mnemonic as f8f6f4; block_scale adds trailing tmem scale-factor operand, no suffix for 1X)
mxf4           tcgen05.mma...kind::mxf4.block_scale.scale_vec::2X               UTCOMMA gdesc[UR12], gdesc[UR14], tmem[UR10], tmem[UR4], idesc[UR5], tmem[UR8], UPT ;  enc 0xc008040e0c0075ea / 0x01e1f4000b80000a  (plain UTCOMMA, no .2X suffix)
mxf4nvf4       tcgen05.mma...kind::mxf4nvf4.block_scale.scale_vec::4X           UTCOMMA.4X gdesc[UR12], gdesc[UR14], tmem[UR10], tmem[UR4], idesc[UR5], tmem[UR8], UPT ;  enc 0x8008040e0c0075ea / 0x01e1f4000b80000a  (only variant with a mnemonic suffix)
f16_sparse     tcgen05.mma.sp.cta_group::1.kind::f16                            UTCHMMA gdesc[UR8], gdesc[UR10], tmem[UR6], tmem[UR4], idesc[UR5], UPT ;  enc 0x00ff040a080075ea / 0x03fbd8000b800006  (same mnemonic/operand shape as dense f16; sparsity encoded only in encoding word 0x03fb.. vs 0x01f9.., and tmem[UR4] carries sparse-metadata address from param instead of URZ)
f16_ws         tcgen05.mma.ws.cta_group::1.kind::f16.collector::b0::fill        UTCHMMA.WS gdesc[UR8], gdesc[UR10].B_KEEP, tmem[UR6], tmem[UR4], idesc[UR5], UPT ;  enc 0x00ff040a080075ea / 0x01f9d8000b8a0006  (.ws -> .WS mnemonic suffix; collector::b0::fill -> .B_KEEP on B descriptor)

cuobjdump -sass default vs -arch sm_100a vs -arch sm_100: all three outputs byte-identical
(diff files empty). The single sm_100a cubin is dumped under both filters; headerflags read
"EF_CUDA_ACCELERATORS EF_CUDA_SM100 EF_CUDA_VIRTUAL_SM(EF_CUDA_SM100)".
nvdisasm output agrees with cuobjdump on every mnemonic (sass_nvdisasm.txt lines 2193-2521).
