from elftools.elf.elffile import ELFFile
import argparse
import pathlib

def print_sections(file, section_name, offset = 0, length = 24):
    with open(file, 'rb') as f:
        elf = ELFFile(f)
        for section in elf.iter_sections():
            if section.name == section_name:
                print(f"Section Name: {section.name}")
                print(f"Section Offset: {section['sh_offset']}")
                print(f"Section Size: {section['sh_size']}")

                # 读取节的内容，返回字节数据
                data = section.data()
                
                # # 打印 从offset开始的length字节内容
                print(data[offset:offset+length])
                print("Hex format:")
                print(data[offset:offset+length].hex())

def find_in_sections(file, section_name, target, start_offset=0):
    """
    在指定的ELF节中从start_offset开始查找目标字节序列。

    :param file: ELF文件的路径。
    :param section_name: 目标节的名称。
    :param target: 目标字节序列（bytes）。
    :param start_offset: 开始搜索的节内偏移量（默认为0）。
    """
    with open(file, 'rb') as f:
        elf = ELFFile(f)
        for section in elf.iter_sections():
            if section.name == section_name:
                data = section.data()
                data_length = len(data)
                target_length = len(target)

                if start_offset >= data_length:
                    print(f"起始偏移量 {start_offset} 超出了节 '{section_name}' 的范围。")
                    return

                # 从start_offset开始搜索
                search_area = data[start_offset:]

                index = search_area.find(target)
                if index != -1:
                    actual_offset = start_offset + index
                    print(f"在节 '{section_name}' 中找到目标 {target.hex()}。")
                    print(f"偏移量: {actual_offset}")
                    return actual_offset
                else:
                    print(f"在节 '{section_name}' 的偏移量 {start_offset} 之后未找到目标 {target.hex()}。")
                    return None
    print(f"未找到节 '{section_name}'。")
    return None

def edit_bytes(file, section_name, offset, new_byte):
    with open(file, 'rb+') as f:
        elf = ELFFile(f)
        for section in elf.iter_sections():
            if section.name == section_name:
                data = section.data()
                if offset < len(data):
                    f.seek(section['sh_offset'] + offset)
                    f.write(new_byte)
                    print(f"Edited {section_name} section at offset {offset}")
                    return

def and_bytes(file, section_name, offset, mask):
    with open(file, 'rb+') as f:
        elf = ELFFile(f)
        for section in elf.iter_sections():
            if section.name == section_name:
                data = section.data()
                mask_len = len(mask)
                if offset + mask_len > len(data):
                    print("偏移量超出节的范围, 无法执行AND操作。")
                    return
                # 定位到指定位置
                f.seek(section['sh_offset'] + offset)
                # 读取现有的字节
                existing = f.read(mask_len)
                if len(existing) < mask_len:
                    print("读取的字节不足, 无法执行AND操作。")
                    return
                # 执行按位与操作
                and_result = bytes([b & m for b, m in zip(existing, mask)])
                # 定位回原位置并写入结果
                f.seek(section['sh_offset'] + offset)
                f.write(and_result)
                print(f"已在节 '{section_name}' 的偏移 {offset} 处执行AND操作, 掩码为 {mask.hex()}")
                return
    print(f"未找到节 '{section_name}'。")

def xor_bytes(file, section_name, offset, mask):
    with open(file, 'rb+') as f:
        elf = ELFFile(f)
        for section in elf.iter_sections():
            if section.name == section_name:
                data = section.data()
                mask_len = len(mask)
                if offset + mask_len > len(data):
                    print("偏移量超出节的范围, 无法执行XOR操作。")
                    return
                # 定位到指定位置
                f.seek(section['sh_offset'] + offset)
                # 读取现有的字节
                existing = f.read(mask_len)
                if len(existing) < mask_len:
                    print("读取的字节不足, 无法执行XOR操作。")
                    return
                # 执行按位异或操作
                xor_result = bytes([b ^ m for b, m in zip(existing, mask)])
                # 定位回原位置并写入结果
                f.seek(section['sh_offset'] + offset)
                f.write(xor_result)
                print(f"已在节 '{section_name}' 的偏移 {offset} 处执行XOR操作, 掩码为 {mask.hex()}")
                return
    print(f"未找到节 '{section_name}'。")

def or_bytes(file, section_name, offset, mask):
    with open(file, 'rb+') as f:
        elf = ELFFile(f)
        for section in elf.iter_sections():
            if section.name == section_name:
                data = section.data()
                mask_len = len(mask)
                if offset + mask_len > len(data):
                    print("偏移量超出节的范围, 无法执行OR操作。")
                    return
                # 定位到指定位置
                f.seek(section['sh_offset'] + offset)
                # 读取现有的字节
                existing = f.read(mask_len)
                if len(existing) < mask_len:
                    print("读取的字节不足, 无法执行OR操作。")
                    return
                # 执行按位或操作
                or_result = bytes([b | m for b, m in zip(existing, mask)])
                # 定位回原位置并写入结果
                f.seek(section['sh_offset'] + offset)
                f.write(or_result)
                print(f"已在节 '{section_name}' 的偏移 {offset} 处执行OR操作, 掩码为 {mask.hex()}")
                return
    print(f"未找到节 '{section_name}'。")



def modify_elf(file, section_name):
    with open(file, 'rb+') as f:
        elf = ELFFile(f)
        for section in elf.iter_sections():
            if section.name == section_name:
                data = section.data()
                # print(data)
                # print(data.hex())
                print(len(data))
        # 找到第一个HMMA指令
        cur_HMMA_Inst_offset = find_in_sections('tf32-1688', '.nv_fatbin', b'\x3c\x72')
        while True:    
            # 查找有无下一个 0x3c72
            next_HMMA_Inst_offset = find_in_sections('tf32-1688', '.nv_fatbin', b'\x3c\x72', start_offset = cur_HMMA_Inst_offset + 1)
            if(next_HMMA_Inst_offset == None):
                print("No next HMMA instruction found.")
                return
            offset_diff = next_HMMA_Inst_offset - cur_HMMA_Inst_offset
            if(offset_diff < 81):
                print(f"Offset diff: {offset_diff}")
                print("Next HMMA instruction found.")
            else:
                print("No next HMMA instruction found.")
                return
            # 检查当前HMMA指令是否reuse rs2(matrix B)
            next_reuse_rs2_offset = find_in_sections('tf32-1688', '.nv_fatbin', b'\x0f\x08', start_offset = cur_HMMA_Inst_offset + 1)
            offset_diff = next_reuse_rs2_offset - cur_HMMA_Inst_offset
            if(offset_diff > 0 and offset_diff < 16):
                print("Reuse rs2(matrix B) detected.")
                print(f"Offset diff: {offset_diff}")             
            else:
                print("No reuse rs2(matrix B) detected.")
                # 修改当前HMMA指令, reuse rs2(matrix B)
                or_bytes('tf32-1688', '.nv_fatbin', cur_HMMA_Inst_offset, b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x08')
                # 查找导致no reuse rs2(matrix B)的 Yield Flag 的 指令
                yield_flag_offset1 = find_in_sections('tf32-1688', '.nv_fatbin', b'\x00\x00\xc2', start_offset = cur_HMMA_Inst_offset + 1)
                yield_flag_offset2 = find_in_sections('tf32-1688', '.nv_fatbin', b'\x00\x00\xc4', start_offset = cur_HMMA_Inst_offset + 1)
                # 如果其中一个为None, 则取另一个, 如果均不为None, 则取较小的
                if(yield_flag_offset1 == None):
                    yield_flag_offset = yield_flag_offset2
                elif(yield_flag_offset2 == None):
                    yield_flag_offset = yield_flag_offset1
                else:
                    yield_flag_offset = min(yield_flag_offset1, yield_flag_offset2)
                offset_diff = yield_flag_offset - cur_HMMA_Inst_offset
                if(offset_diff > 0 and offset_diff < 81):
                    print("Yield Flag detected.")
                    print(f"Offset diff: {offset_diff}")
                    # 取消 Yield Flag
                    or_bytes('tf32-1688', '.nv_fatbin', yield_flag_offset, b'\x00\x00\x20')             
                else:
                    print("No Yield Flag detected.")
                    return
            cur_HMMA_Inst_offset = next_HMMA_Inst_offset


# # print_sections('tf32-1688', '.nv_fatbin', length = 128)
# # find 0x3c72
# Offset = find_in_sections('tf32-1688', '.nv_fatbin', b'\x3c\x72')
# find_in_sections('tf32-1688', '.nv_fatbin', b'\x3c\x72', start_offset = Offset + 1)
# # print(Offset)

# # 示例调用 edit_bytes 函数
# # edit_bytes('tf32-1688', '.nv_fatbin', 36936, b'\x3c\x72\x9c\x20')
# # edit_bytes('tf32-1688', '.nv_fatbin', 36936, b'\x3c\x72')

# # 示例调用 and_bytes 函数
# # and_bytes('tf32-1688', '.nv_fatbin', 36936, b'\xf0\x0f')

# # 示例调用 xor_bytes 函数
# # xor_bytes('tf32-1688', '.nv_fatbin', 36936, b'\xff\x00')

# # 示例调用 or_bytes 函数
# # or_bytes('tf32-1688', '.nv_fatbin', 36936, b'\x0f\xf0')

# # 示例调用 modify_elf 函数
# modify_elf('tf32-1688', '.nv_fatbin')


# print_sections('tf32-1688', '.nv_fatbin', offset = 36936, length = 128)

def main():
    parser = argparse.ArgumentParser(
        prog='editELF',
        description="Edit ELF file."
    )
    parser.add_argument("input_file", type=str, help="Input filename, can only be ELF with embedded cubin.")

    args = parser.parse_args()

    input_file_path = pathlib.Path(args.input_file).absolute()
    modify_elf(input_file_path, '.nv_fatbin')

if __name__ == "__main__":
    main()