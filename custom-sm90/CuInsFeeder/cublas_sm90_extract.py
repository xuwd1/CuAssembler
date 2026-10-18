import os
import pathlib
import subprocess
import tempfile

from tqdm import tqdm

_THIS_SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
TARGET_ARCH_STR = "sm_90"

OUTPUT_DIR = _THIS_SCRIPT_DIR / "sm90_extract"

def get_cublas_so_path() -> pathlib.Path:
    opt_dir = pathlib.Path("/opt")
    cublas_so_path_cands = list(opt_dir.glob("**/libcublas.so"))
    # remove file pathes with "stub"
    cublas_so_path_cands = [path for path in cublas_so_path_cands if "stub" not in path.as_posix()]

    return cublas_so_path_cands[0]

def get_cublas_lt_so_path() -> pathlib.Path:
    opt_dir = pathlib.Path("/opt")
    cublas_lt_so_path_cands = list(opt_dir.glob("**/libcublasLt.so"))
    # remove file pathes with "stub"
    cublas_lt_so_path_cands = [path for path in cublas_lt_so_path_cands if "stub" not in path.as_posix()]

    return cublas_lt_so_path_cands[0]

def extract_sass(
    so_path: pathlib.Path,
    arch_str: str,
    output_path: pathlib.Path
) -> int:
    """Stream SASS for `arch_str` from `so_path` into `output_path`.

    cuobjdump's stdout is attached directly to a temp file in the
    destination directory, so no SASS is buffered in Python; a live byte
    counter is shown while the child runs. `output_path` is atomically
    replaced only after the child exits successfully. Returns the number
    of bytes written.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_file = tempfile.NamedTemporaryFile(
        delete=False,
        mode="wb",
        dir=output_path.parent,
        prefix="." + output_path.name + ".",
        suffix=".tmp",
    )
    tmp_path = pathlib.Path(tmp_file.name)
    command = ["cuobjdump", "-sass", "-arch", arch_str, so_path.as_posix()]
    process = None
    try:
        with tmp_file as output_file:
            process = subprocess.Popen(command, stdout=output_file)
            try:
                with tqdm(total=None, desc=output_path.name, unit="B", unit_scale=True, unit_divisor=1024) as progress:
                    while True:
                        try:
                            process.wait(timeout=0.1)
                            break
                        except subprocess.TimeoutExpired:
                            progress.update(os.fstat(output_file.fileno()).st_size - progress.n)
                    final_size = os.fstat(output_file.fileno()).st_size
                    progress.update(final_size - progress.n)
            except BaseException:
                # kill and reap our own child before the temp file is closed/unlinked
                if process.poll() is None:
                    process.kill()
                    process.wait()
                raise
            if process.returncode != 0:
                raise subprocess.CalledProcessError(process.returncode, command)
        os.replace(tmp_path, output_path)
        return final_size
    finally:
        if process is not None and process.poll() is None:
            process.kill()
            process.wait()
        tmp_path.unlink(missing_ok=True)

def main():
    print(f"Extracting CUBLAS SASS for {TARGET_ARCH_STR}")
    cublas_so_path = get_cublas_so_path()
    print(f"CUBLAS SO path: {cublas_so_path}")
    cublas_sass_size = extract_sass(cublas_so_path, TARGET_ARCH_STR, OUTPUT_DIR / "cublas.sass")
    print(f"CUBLAS SASS written to {OUTPUT_DIR / 'cublas.sass'} ({cublas_sass_size} bytes)")
    
    
    print(f"Extracting CUBLAS LT SASS for {TARGET_ARCH_STR}")
    cublas_lt_so_path = get_cublas_lt_so_path()
    print(f"CUBLAS LT SO path: {cublas_lt_so_path}")
    cublas_lt_sass_size = extract_sass(cublas_lt_so_path, TARGET_ARCH_STR, OUTPUT_DIR / "cublas_lt.sass")
    print(f"CUBLAS LT SASS written to {OUTPUT_DIR / 'cublas_lt.sass'} ({cublas_lt_sass_size} bytes)")
    
    

if __name__ == "__main__":
    main()
