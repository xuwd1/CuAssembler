import sys
import pathlib
import os

_THIS_SCRIPT_DIR = pathlib.Path(__file__).parent
_CuAsm_Containing_DIR = _THIS_SCRIPT_DIR.parent.parent

assert (_CuAsm_Containing_DIR / "LICENCE.md").exists()

sys.path.insert(0, str(_CuAsm_Containing_DIR))

import CuAsm

CUBLAS_LT_LIB_SO_PATH = pathlib.Path("/opt") / "/cuda/targets/x86_64-linux/lib/libcublasLt.so"
CUBLAS_LIB_SO_PATH = pathlib.Path("/opt") / "/cuda/targets/x86_64-linux/lib/libcublas.so"

CUBLAS_LT_LIB_SM90_SASS_PATH = _THIS_SCRIPT_DIR.parent / "sass"/"libcublasLt.sm_90.sass"
CUBLAS_LIB_SM90_SASS_PATH = _THIS_SCRIPT_DIR.parent / "sass"/"libcublas.sm_90.sass"
CUBLAS_LIB_SM90A_SASS_PATH = _THIS_SCRIPT_DIR.parent / "sass"/"libcublas.sm_90a.sass"

ISOLATED_HGMMA_KERNEL_1_SASS_PATH = _THIS_SCRIPT_DIR.parent / "sass"/ "isolated_hgmma_kernel_1.sass"
ISOLATED_HGMMA_KERNEL_2_SASS_PATH = _THIS_SCRIPT_DIR.parent / "sass"/"isolated_hgmma_kernel_2.sass"

ISOLATED_HMMA_KERNEL_1_SASS_PATH = _THIS_SCRIPT_DIR.parent / "sass"/"isolated_hmma_kernel_1.sass"




def try_CuInsFeeder(sass_file_path: pathlib.Path):
    sass_file_path_str = str(sass_file_path)
    feeder = CuAsm.CuInsFeeder(sass_file_path_str)

    print(feeder)

    feeder_iter = iter(feeder)
    addr,code,asm,ctrlcode  = next(feeder_iter)

    '''
        这个ctrlcode是不被包含在code里的.
        也就是说, code和ctrlcode共同组成了整个指令的编码, 二者在指令编码中没有重叠.    
    '''
    print(f"addr: {addr}")
    print(f"code: {code}")
    print(f"asm: {asm}")
    print(f"ctrlcode: {ctrlcode}")

    return

def try_CuInsFeeder_trans(sass_file_path: pathlib.Path):
    sass_file_path_str = str(sass_file_path)
    out_file_path = _THIS_SCRIPT_DIR / (sass_file_path.stem + ".sass.control")
    out_file_path_str = str(out_file_path)
    feeder = CuAsm.CuInsFeeder(sass_file_path_str)

    feeder.trans(out_file_path_str, custom=True)

    

try_CuInsFeeder(ISOLATED_HGMMA_KERNEL_1_SASS_PATH)
try_CuInsFeeder_trans(ISOLATED_HGMMA_KERNEL_1_SASS_PATH)
try_CuInsFeeder_trans(ISOLATED_HMMA_KERNEL_1_SASS_PATH)