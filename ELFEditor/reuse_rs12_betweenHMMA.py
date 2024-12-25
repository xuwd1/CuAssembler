'''
This script is used to try to reuse rs1 and rs2 between 2 consecutive HMMA instructions.
When rs1 or rs2 in the first HMMA instruction is the same as the corresponding register 
in the second HMMA instruction, we can reuse the register.
The script will set the corresponding reuse_flag to 1 in the first HMMA instruction and 
let the yield_flag of the instructions between the two HMMA instructions to be 1.
(yield_flag=0 indicates hardware to switch to another block)
Moreover, the instructions between the two HMMA instructions(such as FMUL) should also try to reuse the rs.

To check the rs1 and rs2 whether can be reused, we need to check 2 things:
1. The rs1 or rs2 in the first HMMA instruction should be the same as the corresponding register in the second HMMA instruction.
2. The rs1 or rs2 in the first HMMA instruction should not be used as rd in the instructions between the two HMMA instructions.
Same as other instructions.
'''

import editELFInst
from editELFInst import Inst
import argparse
import pathlib
from elftools.elf.elffile import ELFFile
import logging

SINGLE_INST_BYTES = 16
INST_WINDOW_SIZE = 5
INST_WINDOW_BYTES = SINGLE_INST_BYTES * INST_WINDOW_SIZE


def reuse_rs12_betweenHMMA(elf_file):
    # get the offset list of all HMMA instructions
    HMMA_instructions_offsets = editELFInst.find_instructions(elf_file, 0x723c)
    print(HMMA_instructions_offsets)
    # for each pair of HMMA instructions(the last one will not be cur_HMMA_Inst)
    for i in range(len(HMMA_instructions_offsets) - 1):
        cur_HMMA_Inst_offset = HMMA_instructions_offsets[i]
        next_HMMA_Inst_offset = HMMA_instructions_offsets[i + 1]

        # check if the distance between 2 consecutive HMMA instructions is smaller than the inst window size
        if(next_HMMA_Inst_offset - cur_HMMA_Inst_offset > INST_WINDOW_BYTES): # larger than the inst window size
            print(f"The distance between two HMMA instructions is larger than the inst window size")
            continue # skip this pair of HMMA instructions
        
        try:
            with open (elf_file, 'rb') as file:
                cur_HMMA_Inst, _ = editELFInst.extract_inst(file, cur_HMMA_Inst_offset)
                next_HMMA_Inst, _ = editELFInst.extract_inst(file, next_HMMA_Inst_offset)

                # check if rs1 and rs2 in the first HMMA instruction is the same as the corresponding register in the second HMMA instruction
                cur_HMMA_Inst_rs1 = cur_HMMA_Inst.get_field('rs1')
                cur_HMMA_Inst_rs2 = cur_HMMA_Inst.get_field('rs2')
                next_HMMA_Inst_rs1 = next_HMMA_Inst.get_field('rs1')
                next_HMMA_Inst_rs2 = next_HMMA_Inst.get_field('rs2')
                reuse_rs1 = (cur_HMMA_Inst_rs1 == next_HMMA_Inst_rs1)
                reuse_rs2 = (cur_HMMA_Inst_rs2 == next_HMMA_Inst_rs2)
                if not reuse_rs1 and not reuse_rs2:
                    continue # skip this pair of HMMA instructions
                
                # check if the rs1 or rs2 in the first HMMA instruction should not be used as rd in the instructions between the two HMMA instructions
                for j in range(cur_HMMA_Inst_offset + SINGLE_INST_BYTES, next_HMMA_Inst_offset, SINGLE_INST_BYTES):
                    inst, _ = editELFInst.extract_inst(file, j)
                    if inst.get_field('rd') == cur_HMMA_Inst_rs1 and  reuse_rs1:
                        reuse_rs1 = False
                    if inst.get_field('rd') == cur_HMMA_Inst_rs2 and  reuse_rs2:
                        reuse_rs2 = False
                    if not reuse_rs1 and not reuse_rs2:
                        break
                
                if not reuse_rs1 and not reuse_rs2:
                    continue # skip this pair of HMMA instructions
                elif reuse_rs1 and reuse_rs2:
                    if cur_HMMA_Inst.get_field('reuse_flag') == 0x3:
                        continue # skip this pair of HMMA instructions since no reuse_flag and yield_flag will be changed
                    editELFInst.set_field(elf_file, cur_HMMA_Inst_offset, 'reuse_flag', 0x3)
                elif reuse_rs1:
                    if cur_HMMA_Inst.get_field('reuse_flag') == 0x1:
                        continue
                    editELFInst.set_field(elf_file, cur_HMMA_Inst_offset, 'reuse_flag', 0x1)
                elif reuse_rs2:
                    if cur_HMMA_Inst.get_field('reuse_flag') == 0x2:
                        continue
                    editELFInst.set_field(elf_file, cur_HMMA_Inst_offset, 'reuse_flag', 0x2)
                else:
                    raise Exception("Unknown reuse case")
                    
                # since the reuse_flag of the first HMMA instruction is changed,
                # set the yield_flag of the instructions between the two HMMA instructions to be 1
                no_yield_range = range(cur_HMMA_Inst_offset, next_HMMA_Inst_offset, SINGLE_INST_BYTES) # [start, stop)
                end_of_no_yield_range = cur_HMMA_Inst_offset
                
                # TODO: check if the rs1 or rs2 of instructions in the range should be reused
                # if there is repeated rs1 or rs2 in the window_size for an instruction
                # use 2 hash tables to store the rs1 and rs2 of the instructions
                rs1_hash = {}
                rs2_hash = {}

                # define the first phase and the second phase
                # first phase: [cur_HMMA_Inst_offset + 16, next_HMMA_Inst_offset)
                # second phase : [next_HMMA_Inst_offset + 16, next_HMMA_Inst_offset + INST_WINDOW_BYTES)
                for j in range(cur_HMMA_Inst_offset + SINGLE_INST_BYTES, next_HMMA_Inst_offset + INST_WINDOW_BYTES, SINGLE_INST_BYTES):
                    inst, _ = editELFInst.extract_inst(file, j)
                    rs1 = inst.get_field('rs1')
                    rs2 = inst.get_field('rs2')
                    rd = inst.get_field('rd')

                    # cheek if the rs1 of the current instruction can be reused
                    if rs1 in rs1_hash:
                        editELFInst.set_field(elf_file, rs1_hash[rs1], 'reuse_rs1', 0x1)
                        del rs1_hash[rs1]
                        end_of_no_yield_range = max(j, next_HMMA_Inst_offset)

                    # cheek if the rs2 of the current instruction can be reused
                    if rs2 in rs2_hash:
                        editELFInst.set_field(elf_file, rs2_hash[rs2], 'reuse_rs2', 0x1)
                        del rs2_hash[rs2]
                        end_of_no_yield_range = max(j, next_HMMA_Inst_offset)

                    if rd in rs1_hash:
                        del rs1_hash[rd]
                    if rd in rs2_hash:
                        del rs2_hash[rd]

                    if j < next_HMMA_Inst_offset:
                        rs1_hash[rs1] = j
                        rs2_hash[rs2] = j

                # update no_yield_range
                no_yield_range = range(cur_HMMA_Inst_offset, end_of_no_yield_range, SINGLE_INST_BYTES)

                # set yield_flag to 1
                for j in no_yield_range:
                # for j in range(cur_HMMA_Inst_offset, next_HMMA_Inst_offset, SINGLE_INST_BYTES):
                    inst, _ = editELFInst.extract_inst(file, j)
                    if inst.get_field('yield_flag') == 0:
                        editELFInst.set_field(elf_file, j, 'yield_flag', 1) # set yield_flag to 1


        except IOError as e:
            logging.error(f"IO error occurred: {e}")
        except Exception as e:
            logging.error(f"An unexpected error occurred: {e}")


def main():
    parser = argparse.ArgumentParser(
        prog='reuse_rs12_betweenHMMA',
        description="Reuse rs2 in HMMA instruction and cancel yield flag which leads to no reuse.",
    )
    # subparsers = parser.add_subparsers(dest='command', help='Sub-command help')

    parser.add_argument("input_file", type=str, help="Input filename, can only be ELF with embedded cubin.")

    args = parser.parse_args()

    input_file_path = pathlib.Path(args.input_file).absolute()

    reuse_rs12_betweenHMMA(input_file_path)


if __name__ == "__main__":
    main()