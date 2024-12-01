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

def try_CuInsParser(sass_file_path: pathlib.Path):
    sass_file_path_str = str(sass_file_path)
    feeder = CuAsm.CuInsFeeder(sass_file_path_str)

    cip = CuAsm.CuInsParser(arch = "sm_90")

    for addr, code, asm, ctrlcode in feeder:
        ins_key, ins_val, ins_modi = cip.parse(asm, addr, code)


try_CuInsParser(ISOLATED_HGMMA_KERNEL_1_SASS_PATH)