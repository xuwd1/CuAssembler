import editELFInst
from editELFInst import Inst
import argparse
import pathlib
from elftools.elf.elffile import ELFFile
import logging

# def extract_inst(file_obj, byte_offset: int) -> Tuple[Inst, int]:
#     """
#     从 ELF 文件的 .nv_fatbin 段中提取指定 byte_offset 处的 Inst 对象。

#     :param file_obj: 已打开的 ELF 文件对象。
#     :param byte_offset: 指令的段内字节偏移量。
#     :return: 一个包含 Inst 对象和段的文件偏移量的元组。
#     """

def reuse_rs2_inHMMA(elf_file):
    HMMA_instructions_offsets = editELFInst.find_instructions(elf_file, 0x723c)
    print(HMMA_instructions_offsets)
    # 对于除了最后一条指令之外的所有指令
    for i in range(len(HMMA_instructions_offsets) - 1):
        cur_HMMA_Inst_offset = HMMA_instructions_offsets[i]
        next_HMMA_Inst_offset = HMMA_instructions_offsets[i + 1]

        if(next_HMMA_Inst_offset - cur_HMMA_Inst_offset > 16*5):
            print(f"Finish processing a part.")
            continue
        
        try:
            with open (elf_file, 'rb') as f:
                cur_HMMA_Inst, _ = editELFInst.extract_inst(f, cur_HMMA_Inst_offset)
                # print(f"cur_HMMA_Inst: {cur_HMMA_Inst}")
                if cur_HMMA_Inst.get_field('reuse_flag') == 0x2: # 如果 reuse_flag 为 2, 说明已经 reuse 了 rs2
                    continue
                editELFInst.set_field(elf_file, cur_HMMA_Inst_offset, 'reuse_flag', 0x2) # 否则说明没有 reuse rs2, 将 reuse_flag 设置为 2

                # 还要处理两条HMMA之间指令的 yield_flag, 从cur_HMMA_Inst_offset到next_HMMA_Inst_offset, yield_flag应该都为1
                for j in range(cur_HMMA_Inst_offset + 16, next_HMMA_Inst_offset, 16):
                    inst, _ = editELFInst.extract_inst(f, j)
                    if inst.get_field('yield_flag') == 0:
                        editELFInst.set_field(elf_file, j, 'yield_flag', 1)


        except IOError as e:
            logging.error(f"IO error occurred: {e}")
        except Exception as e:
            logging.error(f"An unexpected error occurred: {e}")


def main():
    parser = argparse.ArgumentParser(
        prog='reuse_rs2_inHMMA',
        description="Reuse rs2 in HMMA instruction and cancel yield flag which leads to no reuse.",
    )
    # subparsers = parser.add_subparsers(dest='command', help='Sub-command help')

    parser.add_argument("input_file", type=str, help="Input filename, can only be ELF with embedded cubin.")

    args = parser.parse_args()

    input_file_path = pathlib.Path(args.input_file).absolute()

    reuse_rs2_inHMMA(input_file_path)


if __name__ == "__main__":
    main()