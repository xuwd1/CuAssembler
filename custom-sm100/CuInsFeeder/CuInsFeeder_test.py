import sys
import pathlib

_THIS_SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
_CUSTOM_SM100_DIR = _THIS_SCRIPT_DIR.parent
_CUASM_CONTAINING_DIR = _THIS_SCRIPT_DIR.parent.parent
assert (_CUASM_CONTAINING_DIR / "LICENCE.md").exists()

sys.path.insert(0, str(_CUASM_CONTAINING_DIR))
import CuAsm

_TRANS_OUTPUT_DIR = _THIS_SCRIPT_DIR / "trans_output"


SM100_ISOLATED_UTCIMMA_KERNEL_1_SASS_PATH = _CUSTOM_SM100_DIR / "sass" / "isolated_utcimma_kernel_1.sass"
SM100_ISOLATED_HMMA_KERNEL_1_SASS_PATH = _CUSTOM_SM100_DIR / "sass" / "isolated_hmma_kernel_1.sass"

assert SM100_ISOLATED_UTCIMMA_KERNEL_1_SASS_PATH.exists()
assert SM100_ISOLATED_HMMA_KERNEL_1_SASS_PATH.exists()

def try_CuInsFeeder(sass_file_path: pathlib.Path):
    sass_file_path_str = str(sass_file_path)
    feeder = CuAsm.CuInsFeeder(sass_file_path_str)
    try:
        print(feeder)

        count = 0
        for addr, code, asm, ctrlcode in feeder:
            if count == 0:
                '''
                    这个ctrlcode是不被包含在code里的.
                    也就是说, code和ctrlcode共同组成了整个指令的编码, 二者在指令编码中没有重叠.
                '''
                print(f"addr: {addr}")
                print(f"code: {code}")
                print(f"asm: {asm}")
                print(f"ctrlcode: {ctrlcode}")
            count += 1

        print(f"total instructions: {count}")
    finally:
        feeder.close()

def try_CuInsFeeder_trans(sass_file_path: pathlib.Path):
    sass_file_path_str = str(sass_file_path)
    _TRANS_OUTPUT_DIR.mkdir(exist_ok=True)
    out_file_path = _TRANS_OUTPUT_DIR / (sass_file_path.stem + ".sass.control")
    out_file_path_str = str(out_file_path)
    feeder = CuAsm.CuInsFeeder(sass_file_path_str)
    try:
        # Isolated sass dumps carry no resource-usage data, so pass an empty map.
        feeder.trans(out_file_path_str, custom=True, res_usage_dict={})
    finally:
        feeder.close()

    print(f"trans output: {out_file_path}")

def main():
    for sass_file_path in (SM100_ISOLATED_UTCIMMA_KERNEL_1_SASS_PATH,
                           SM100_ISOLATED_HMMA_KERNEL_1_SASS_PATH):
        try_CuInsFeeder(sass_file_path)
        try_CuInsFeeder_trans(sass_file_path)

if __name__ == '__main__':
    main()
