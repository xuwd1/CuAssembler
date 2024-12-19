#! /usr/bin/python3


import os
import sys
import pathlib
import re

from subprocess import CalledProcessError, check_output
import shutil
from io import StringIO
from CuAsm.CuInsFeeder import CuInsFeeder
from CuAsm.CuAsmLogger import CuAsmLogger
from CuAsm.utils.CubinUtils import fixCubinDesc
from CuAsm.common import getTempFileName
import argparse
from dataclasses import dataclass

@dataclass
class ResUsageStat:
    REG: int
    STACK: int
    SHARED: int
    LOCAL: int
    CONSTANT_0: int
    TEXTURE: int
    SURFACE: int
    SAMPLER: int

    @staticmethod
    def from_cuobjdump_line(line: str):
        REG_extract_re = r"REG:(\d+)"
        STACK_extract_re = r"STACK:(\d+)"
        SHARED_extract_re = r"SHARED:(\d+)"
        LOCAL_extract_re = r"LOCAL:(\d+)"
        CONSTANT_0_extract_re = r"CONSTANT\[0\]:(\d+)"
        TEXTURE_extract_re = r"TEXTURE:(\d+)"
        SURFACE_extract_re = r"SURFACE:(\d+)"
        SAMPLER_extract_re = r"SAMPLER:(\d+)"

        reg = int(re.search(REG_extract_re, line).group(1))
        stack = int(re.search(STACK_extract_re, line).group(1))
        shared = int(re.search(SHARED_extract_re, line).group(1))
        local = int(re.search(LOCAL_extract_re, line).group(1))
        constant_0 = int(re.search(CONSTANT_0_extract_re, line).group(1))
        texture = int(re.search(TEXTURE_extract_re, line).group(1))
        surface = int(re.search(SURFACE_extract_re, line).group(1))
        sampler = int(re.search(SAMPLER_extract_re, line).group(1))

        return ResUsageStat(
            REG=reg,
            STACK=stack,
            SHARED=shared,
            LOCAL=local,
            CONSTANT_0=constant_0,
            TEXTURE=texture,
            SURFACE=surface,
            SAMPLER=sampler
        )
    
    def __str__(self):
        return f"REG:{self.REG} STACK:{self.STACK} SHARED:{self.SHARED} LOCAL:{self.LOCAL} CONSTANT[0]:{self.CONSTANT_0} TEXTURE:{self.TEXTURE} SURFACE:{self.SURFACE} SAMPLER:{self.SAMPLER}"
        
def build_usage_dict(
        input_file_path: pathlib.Path
    ):
    Function_extract_re = r"^\s*Function\s*(\w+):"
    res_usage_report_b = check_output(['cuobjdump', '-res-usage', str(input_file_path)])
    res_usage_report = res_usage_report_b.decode()
    res_usage_report_lines = res_usage_report.split("\n")

    ret_dict = {}
    
    for line_idx, line in enumerate(res_usage_report_lines):
        if re.match(Function_extract_re, line):
            func_name = re.match(Function_extract_re, line).group(1)
            res_usage_stat = ResUsageStat.from_cuobjdump_line(res_usage_report_lines[line_idx + 1])
            ret_dict[func_name] = res_usage_stat
    return ret_dict



def do_trans(
        input_file_path: pathlib.Path,
        output_file_path: pathlib.Path
    ):

    res_usage_dict = build_usage_dict(input_file_path)
    
    sass_b = check_output(['cuobjdump', '-sass', str(input_file_path)])
    sass = sass_b.decode()
    sass_string_io = StringIO(sass)

    # print("sass_string_io", sass_string_io)
    # content = sass_string_io.read()
    # print(content)

    feeder = CuInsFeeder(sass_string_io)
    feeder.trans(str(output_file_path), custom=True, res_usage_dict=res_usage_dict)


def main():
    parser = argparse.ArgumentParser(
        prog='trans',
        description="Translate ELF embedded cubin to SASS with control codes"
    )
    parser.add_argument("input_file", type=str, help="Input filename, can only be ELF with embedded cubin.")
    parser.add_argument("-o", "--output_file", type=str, help="Output filename, inferred from input filename if not given.", default=None)

    args = parser.parse_args()

    input_file_path = pathlib.Path(args.input_file).absolute()
    if args.output_file is None:
        output_file_path = input_file_path.with_suffix(".sass.control")
    else:
        output_file_path = pathlib.Path(args.output_file).absolute()

    do_trans(input_file_path, output_file_path)

if __name__ == "__main__":
    main()

