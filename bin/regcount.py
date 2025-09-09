#! /usr/bin/python3


import os
import sys
import pathlib
import re
from typing import List, Dict, Tuple
from dataclasses import dataclass
import argparse

@dataclass
class FuncLinesInfo:
    # mangled func name
    func_name: str
    # inclusive start index
    func_start_line_idx: int
    # exclusive end index
    func_end_line_idx: int
    need_count: bool
    count_line_insertion_relative_idx: int


def split_functions(
    input_file_lines: List[str]
) -> List[FuncLinesInfo]:
    func_start_string_re = re.compile(r'^[ \t]{2,}Function : (.*)$')
    insertion_re = re.compile(r'^[ \t]{2,}Resource Usage.*$')
    # inclusive start indices
    func_start_indices = []
    insertion_abs_indices = []
    func_names = []
    for idx, line in enumerate(input_file_lines):
        m = func_start_string_re.match(line)
        if m:
            func_start_indices.append(idx)
            func_names.append(m.group(1))
        m = insertion_re.match(line)
        if m:
            insertion_abs_indices.append(idx)
    
    if len(func_start_indices) == 0:
        raise ValueError("No function found in the input file lines.")
    # exclusive end indices
    func_end_indices = func_start_indices[1:] + [len(input_file_lines)]

    func_lines_info_list = []
    for i in range(len(func_start_indices)):
        func_lines_info_list.append(
            FuncLinesInfo(
                func_name=func_names[i],
                func_start_line_idx=func_start_indices[i],
                func_end_line_idx=func_end_indices[i],
                need_count=True,
                count_line_insertion_relative_idx=(
                    insertion_abs_indices[i] - func_start_indices[i]
                )
            )
        )

    # insert a file header line info at the beginning
    header_func_lines_info = FuncLinesInfo(
        func_name="__file_header__",
        func_start_line_idx=0,
        func_end_line_idx=func_start_indices[0],
        need_count=False,
        count_line_insertion_relative_idx=-1
    )
    func_lines_info_list.insert(0, header_func_lines_info)

    return func_lines_info_list

def extract_func_lines(
    input_file_lines: List[str],
    func_lines_info: FuncLinesInfo
) -> List[str]:
    return input_file_lines[
        func_lines_info.func_start_line_idx:
        func_lines_info.func_end_line_idx
    ]

def count_function_regs(
    func_lines: List[str]
) -> Tuple[int, int]: # returns max (R, UR) indices + 1
    reg_pattern = re.compile(r'\bR(\d+)\b')
    ureg_pattern = re.compile(r'\bUR(\d+)\b')

    all_reg_indices = set()
    all_ureg_indices = set()
    for l in func_lines:
        for m in reg_pattern.finditer(l):
            all_reg_indices.add(int(m.group(1)))
        for m in ureg_pattern.finditer(l):
            all_ureg_indices.add(int(m.group(1)))

    return (
        1 + (max(all_reg_indices) if len(all_reg_indices)>0 else -1),
        1 + (max(all_ureg_indices) if len(all_ureg_indices)>0 else -1)
)

def run_regcount_on_file(
    input_file_path: pathlib.Path,
    output_file_path: pathlib.Path
):
    input_file_lines = []
    with open(input_file_path, 'r') as fin:
        input_file_lines = fin.readlines()
    func_lines_info_list = split_functions(input_file_lines)

    output_lines = []
    for func_lines_info in func_lines_info_list:
        if func_lines_info.need_count:
            lines = extract_func_lines(input_file_lines, func_lines_info)
            R_count, UR_count = count_function_regs(lines)
            insertion_idx = func_lines_info.count_line_insertion_relative_idx
            regcount_report_line = "\t\tCounted Resource Usage : R:{}, UR:{}\n".format(R_count, UR_count)
            lines.insert(insertion_idx + 1, regcount_report_line)
            output_lines.extend(lines)
        else:
            lines = extract_func_lines(input_file_lines, func_lines_info)
            output_lines.extend(lines)
    
    # write out
    with open(output_file_path, 'w') as fout:
        fout.writelines(output_lines)


def main():
    parser = argparse.ArgumentParser(
    )
    parser.add_argument(
        'input_transed_sass_file_path',
        type=pathlib.Path,
        help="Input SASS file path that has been translated with control codes, with the trans tool."
    )
    parser.add_argument(
        '-o', '--output_file_path',
        type=pathlib.Path,
        default=None,
    )
    args = parser.parse_args()
    
    input_file_path = pathlib.Path(args.input_transed_sass_file_path).absolute()
    if not input_file_path.exists():
        print("Input file does not exist:", str(input_file_path))
        sys.exit(1)
    if args.output_file_path is None:
        output_file_path = input_file_path.with_suffix(".control.regcount")
    else:
        output_file_path = args.output_file_path.absolute()

    run_regcount_on_file(input_file_path, output_file_path)



if __name__ == "__main__":
    main()
