#! /usr/bin/python3


import os
import sys
import pathlib

from subprocess import CalledProcessError, check_output
import shutil
from io import StringIO
from CuAsm.CuInsFeeder import CuInsFeeder
from CuAsm.CuAsmLogger import CuAsmLogger
from CuAsm.utils.CubinUtils import fixCubinDesc
from CuAsm.common import getTempFileName
import argparse



def do_trans(
        input_file_path: pathlib.Path,
        output_file_path: pathlib.Path
    ):
    
    sass_b = check_output(['cuobjdump', '-sass', str(input_file_path)])
    sass = sass_b.decode()
    sass_string_io = StringIO(sass)

    feeder = CuInsFeeder(sass_string_io)
    feeder.trans(str(output_file_path), custom=True)


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

