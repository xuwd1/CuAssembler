import re
from CuAsm.CuNVInfo import CuNVInfo
import argparse

"""
A simple tool for comparing the EIATTRs in nvdisasm generated disassembly
and the known EIATTRs defined in CuNVInfo.EIATTR

This tool works by matching every EIATTR found in nvdisasm generated
disassembly with the known EIATTRs. If unmatched EIATTR is found it 
would report it to stdout.
"""


EIATTR_strlist = [
    item for key,item in CuNVInfo.EIATTR.items()
]


# NOTE: here the file should be a nvdisasm generated disassembly
def read_cuasm(filepath:str):
    with open(filepath) as f:
        lines = f.readlines()
    return lines

def extract_eiattr_strs(str_lines:list[str]):
    regex_eiattr = re.compile(r"EIATTR.*")
    ret = []
    for line in str_lines:
        m = regex_eiattr.search(line)
        if m is not None:
            m_str = m.group()
            ret.append(m_str)

    return ret

def crosscheck(extracted_eiattrs, candidate_eiattrs):
    found_unmatched = False
    for e_eiattr in extracted_eiattrs:
        if e_eiattr in candidate_eiattrs:
            continue
        else:
            print("Found unmatched eiattr: {}".format(e_eiattr))
            found_unmatched = True

    if not found_unmatched:
        print("All EIATTRs matched")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog = 'compareEIATTR',
        description = 'A simple tool for comparing the EIATTRs in nvdisasm generated disassembly and the known EIATTRs defined in CuNVInfo.EIATTR'
    )
    parser.add_argument('path',metavar='PATH',type=str)
    args = parser.parse_args()
    lines = read_cuasm(args.path)
    extracted_eiattrs = extract_eiattr_strs(lines)
    crosscheck(extracted_eiattrs, EIATTR_strlist)