from elftools.elf.elffile import ELFFile
import argparse
import pathlib
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import logging
import instruction_config  # 导入配置模块

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

COMMON_FIELDS = instruction_config.COMMON_FIELDS
INSTRUCTION_TYPES = instruction_config.INSTRUCTION_TYPES

def identify_instruction_type(inst):
    """
    根据 opcode1 和 opcode2 识别指令类型。
    
    :param inst: Inst 对象
    :return: 指令类型配置字典
    """
    for instr_type in INSTRUCTION_TYPES:
        # 如果指令类型有 opcode1 进行匹配
        if instr_type["opcode1"] is not None and inst.get_opcode1() != instr_type["opcode1"]:
            continue
        # 如果指令类型有 opcode2 进行匹配
        if instr_type["opcode2"] is not None and inst.get_opcode2() != instr_type["opcode2"]:
            continue
        # 匹配成功
        return instr_type
    return None  # 未识别的指令类型

@dataclass
class Inst:
    raw_bytes: bytes  # 16字节的原始指令数据
    value: int = field(init=False)  # 不在初始化参数中
    instr_type: Optional[Dict] = field(init=False, default=None)  # 指令类型配置

    def __post_init__(self):
        if len(self.raw_bytes) != 16:
            raise ValueError("Inst must be exactly 16 bytes long.")
        # 将字节数据转换为整数，考虑小端字节序
        self.value = int.from_bytes(self.raw_bytes, byteorder='little')
        # 识别指令类型
        self.instr_type = identify_instruction_type(self)

    def get_bit(self, bit_index: int) -> int:
        """
        获取指令中指定的位（0-127）。
        0表示最低位，127表示最高位。
        """
        if not 0 <= bit_index < 128:
            raise ValueError("bit_index must be in range 0-127.")
        return (self.value >> bit_index) & 1

    def set_bit(self, bit_index: int, bit_value: int):
        """
        设置指令中指定的位（0-127）。
        bit_value应为0或1。
        """
        if not 0 <= bit_index < 128:
            raise ValueError("bit_index must be in range 0-127.")
        if bit_value not in (0, 1):
            raise ValueError("bit_value must be 0 or 1.")
        if bit_value:
            self.value |= (1 << bit_index)
        else:
            self.value &= ~(1 << bit_index)

    def get_bits(self, start: int, length: int) -> int:
        """
        获取从 start 位开始的 length 位的值。
        """
        if not (0 <= start < 128) or not (1 <= length <= 128 - start):
            raise ValueError("Invalid start or length for bit extraction.")
        mask = (1 << length) - 1
        return (self.value >> start) & mask

    def set_bits(self, start: int, length: int, bits_value: int):
        """
        设置从 start 位开始的 length 位为 bits_value。
        """
        if not (0 <= start < 128) or not (1 <= length <= 128 - start):
            raise ValueError("Invalid start or length for bit setting.")
        mask = ((1 << length) - 1) << start
        if bits_value < 0 or bits_value >= (1 << length):
            raise ValueError("bits_value out of range for the specified length.")
        self.value = (self.value & ~mask) | ((bits_value << start) & mask)

    def get_field(self, field_name: str) -> Optional[int]:
        """
        获取指令中指定字段的值。
        
        :param field_name: 字段名称（如 'reuse_flag', 'opcode1', 'opcode2', 'control_code'）
        :return: 字段值，或 None 如果字段不存在
        """
        # 首先检查通用字段
        if field_name in COMMON_FIELDS:
            start, end = COMMON_FIELDS[field_name]
            length = end - start + 1
            return self.get_bits(start, length)
        
        # 然后检查指令类型特有字段
        if self.instr_type:
            fields = self.instr_type.get("fields", {})
            field_bits = fields.get(field_name)
            if field_bits:
                start, end = field_bits  # 结束位是包含的
                length = end - start + 1
                return self.get_bits(start, length)
        return None

    def set_field(self, field_name: str, field_value: int):
        """
        设置指令中指定字段的值。
        
        :param field_name: 字段名称（如 'reuse_flag', 'opcode1', 'opcode2', 'control_code'）
        :param field_value: 新的字段值
        """
        # 首先检查通用字段
        if field_name in COMMON_FIELDS:
            start, end = COMMON_FIELDS[field_name]
            length = end - start + 1
            self.set_bits(start, length, field_value)
            return
        
        # 然后检查指令类型特有字段
        if self.instr_type:
            fields = self.instr_type.get("fields", {})
            field_bits = fields.get(field_name)
            if field_bits:
                start, end = field_bits
                length = end - start + 1
                self.set_bits(start, length, field_value)
                return
        
        raise ValueError(f"Field '{field_name}' not found in either common fields or instruction type '{self.instr_type['name'] if self.instr_type else 'Unknown'}'.")

    def get_opcode1(self) -> int:
        """
        获取指令的 opcode1（位 0-15）。
        """
        return self.get_field("opcode1")

    def get_opcode2(self) -> int:
        """
        获取指令的 opcode2（位 72-87）。
        """
        return self.get_field("opcode2")

    def get_control_code(self) -> int:
        """
        获取指令的 control_code（位 16-31）。
        """
        return self.get_field("control_code")

    def set_control_code(self, control_code: int):
        """
        设置指令的 control_code（位 16-31）。
        """
        self.set_field("control_code", control_code)

    def get_field_names(self) -> List[str]:
        """
        获取指令中所有可用的字段名称。
        """
        field_names = list(COMMON_FIELDS.keys())
        if self.instr_type:
            field_names.extend(self.instr_type.get("fields", {}).keys())
        return field_names

    def to_bytes(self) -> bytes:
        """
        将整数值转换回16字节的字节序列，使用小端字节序。
        """
        return self.value.to_bytes(16, byteorder='little')

    def __repr__(self):
        fields_repr = ", ".join([f"{name}=0x{self.get_field(name):x}" for name in self.get_field_names() if self.get_field(name) is not None])
        if self.instr_type:
            return f"Inst(value=0x{self.value:032x}, type={self.instr_type['name']}, {fields_repr})"
        else:
            return f"Inst(value=0x{self.value:032x}, type=Unknown, {fields_repr})"

def extract_inst(file_obj, byte_offset: int) -> Tuple[Inst, int]:
    """
    从 ELF 文件的 .nv_fatbin 段中提取指定 byte_offset 处的 Inst 对象。

    :param file_obj: 已打开的 ELF 文件对象。
    :param byte_offset: 指令的段内字节偏移量。
    :return: 一个包含 Inst 对象和段的文件偏移量的元组。
    """
    section_name = '.nv_fatbin'
    inst_size = 16

    elf = ELFFile(file_obj)
    for section in elf.iter_sections():
        if section.name == section_name:
            section_data = section.data()
            if byte_offset + inst_size > len(section_data):
                raise ValueError("Instruction offset out of range.")
            
            # 计算文件中的实际偏移量
            file_offset = section['sh_offset'] + byte_offset
            file_obj.seek(file_offset)
            inst_bytes = file_obj.read(inst_size)
            inst = Inst(inst_bytes)
            return inst, section['sh_offset']
    
    raise ValueError(f"Section {section_name} not found in ELF file.")

def edit_inst_bit(file_path: str, byte_offset: int, bit_index: int, new_bit: int):
    """
    编辑指定 ELF 文件中 .nv_fatbin 段的某条指令的特定位。

    :param file_path: ELF 文件路径。
    :param byte_offset: 指令的段内字节偏移量。
    :param bit_index: 要修改的位索引（0-127）。
    :param new_bit: 新的位值（0 或 1）。
    """
    try:
        with open(file_path, 'rb+') as f:
            inst, sh_offset = extract_inst(f, byte_offset)
            
            logging.info(f"Original instruction at byte {byte_offset}: {inst}")
            current_bit = inst.get_bit(bit_index)
            logging.info(f"Bit {bit_index} before: {current_bit}")
            
            inst.set_bit(bit_index, new_bit)
            
            logging.info(f"Modified instruction: {inst}")
            
            # 将修改后的指令写回文件
            f.seek(sh_offset + byte_offset)
            f.write(inst.to_bytes())
            
            logging.info(f"Edited .nv_fatbin section at bytes {byte_offset}, bit {bit_index} set to {new_bit}")
    except IOError as e:
        logging.error(f"IO error occurred: {e}")
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}")

def print_inst(file_path: str, byte_offset: int):
    """
    打印 ELF 文件中 .nv_fatbin 段的指定字节偏移处的指令。

    :param file_path: ELF 文件路径。
    :param byte_offset: 指令的段内字节偏移量。
    """
    try:
        with open(file_path, 'rb') as f:
            inst, _ = extract_inst(f, byte_offset)
            print(f"Instruction at byte {byte_offset}: {inst}")
    except IOError as e:
        logging.error(f"IO error occurred: {e}")
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}")

def find_instructions(file_path: str, opcode1: Optional[int] = None, opcode2: Optional[int] = None, aligned: bool = False) -> List[int]:
    """
    在 .nv_fatbin section 中查找匹配 opcode1 和/或 opcode2 的指令，返回它们的段内 byte_offset。

    :param file_path: ELF 文件路径。
    :param opcode1: 要匹配的 opcode1（可选）。
    :param opcode2: 要匹配的 opcode2（可选）。
    :param aligned: 是否按指令对齐（默认 False）。
    :return: 匹配指令的段内 byte_offset 列表。
    """
    if opcode1 is None and opcode2 is None:
        raise ValueError("至少需要提供 opcode1 或 opcode2 进行匹配。")
    
    matching_offsets = []
    
    try:
        with open(file_path, 'rb') as f:
            elf = ELFFile(f)
            for section in elf.iter_sections():
                if section.name == '.nv_fatbin':
                    section_data = section.data()
                    data_length = len(section_data)
                    inst_size = 16
                    
                    if aligned:
                        # 假设指令按16字节对齐
                        for byte_offset in range(0, data_length - inst_size + 1, inst_size):
                            inst_bytes = section_data[byte_offset:byte_offset + inst_size]
                            try:
                                inst = Inst(inst_bytes)
                            except ValueError:
                                continue  # 跳过无效的指令长度
                            
                            if not inst.instr_type:
                                continue  # 未识别的指令类型
                            
                            match = True
                            if opcode1 is not None and inst.get_opcode1() != opcode1:
                                match = False
                            if opcode2 is not None and inst.get_opcode2() != opcode2:
                                match = False
                            
                            if match:
                                matching_offsets.append(byte_offset)
                    else:
                        # 非对齐搜索
                        for byte_offset in range(data_length - inst_size + 1):  # 16字节的窗口
                            inst_bytes = section_data[byte_offset:byte_offset + inst_size]
                            try:
                                inst = Inst(inst_bytes)
                            except ValueError:
                                continue  # 跳过无效的指令长度
                            
                            if not inst.instr_type:
                                continue  # 未识别的指令类型
                            
                            match = True
                            if opcode1 is not None and inst.get_opcode1() != opcode1:
                                match = False
                            if opcode2 is not None and inst.get_opcode2() != opcode2:
                                match = False
                            
                            if match:
                                matching_offsets.append(byte_offset)
                    
                    return matching_offsets
        raise ValueError(f"Section .nv_fatbin not found in ELF file.")
    except IOError as e:
        logging.error(f"IO error occurred: {e}")
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}")
    
    return matching_offsets  # 返回空列表，如果发生错误

def set_field(file_path: str, byte_offset: int, field_name: str, field_value: int):
    """
    设置 ELF 文件中 .nv_fatbin 段的指定字节偏移处指令的某个字段。

    :param file_path: ELF 文件路径。
    :param byte_offset: 指令的段内字节偏移量。
    :param field_name: 字段名称（如 'reuse_flag'）。
    :param field_value: 新的字段值。
    """
    try:
        with open(file_path, 'rb+') as f:
            inst, sh_offset = extract_inst(f, byte_offset)
            
            if not inst.instr_type:
                raise ValueError("Instruction type not recognized; cannot modify fields.")
            
            current_field = inst.get_field(field_name)
            if current_field is None:
                raise ValueError(f"Field '{field_name}' not found in instruction type '{inst.instr_type['name']}'.")
    
            logging.info(f"Original {field_name} at byte {byte_offset}: {current_field}")
            
            inst.set_field(field_name, field_value)
            
            logging.info(f"Modified {field_name} to {field_value} at byte {byte_offset}: {inst}")
            
            # 将修改后的指令写回文件
            f.seek(sh_offset + byte_offset)
            f.write(inst.to_bytes())
            
            logging.info(f"Set field '{field_name}' to {field_value} in instruction at byte {byte_offset}")
    except IOError as e:
        logging.error(f"IO error occurred: {e}")
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}")

def main():
    parser = argparse.ArgumentParser(
        prog='editELFInst',
        description="Edit ELF file Inst."
    )
    subparsers = parser.add_subparsers(dest='command', help='Sub-command help')

    # Sub-command: print
    parser_print = subparsers.add_parser('print', help='Print instruction at byte offset')
    parser_print.add_argument("input_file", type=str, help="Input ELF filename.")
    parser_print.add_argument("byte_offset", type=int, help="Byte offset of the instruction.")

    # Sub-command: edit_bit
    parser_edit = subparsers.add_parser('edit_bit', help='Edit a bit in an instruction')
    parser_edit.add_argument("input_file", type=str, help="Input ELF filename.")
    parser_edit.add_argument("byte_offset", type=int, help="Byte offset of the instruction.")
    parser_edit.add_argument("bit_index", type=int, help="Bit index to modify (0-127).")
    parser_edit.add_argument("new_bit", type=int, choices=[0, 1], help="New bit value (0 or 1).")

    # Sub-command: search
    parser_search = subparsers.add_parser('search', help='Search for instructions by opcode1 and/or opcode2')
    parser_search.add_argument("input_file", type=str, help="Input ELF filename.")
    parser_search.add_argument("--opcode1", type=lambda x: int(x,0), help="Opcode1 value to match (e.g., 0x1234).")
    parser_search.add_argument("--opcode2", type=lambda x: int(x,0), help="Opcode2 value to match (e.g., 0xABCD).")
    parser_search.add_argument("--aligned", action='store_true', help="Search assuming 16-byte aligned instructions.")

    # Sub-command: set_field
    parser_set_field = subparsers.add_parser('set_field', help='Set a field in an instruction')
    parser_set_field.add_argument("input_file", type=str, help="Input ELF filename.")
    parser_set_field.add_argument("byte_offset", type=int, help="Byte offset of the instruction.")
    parser_set_field.add_argument("field_name", type=str, help="Field name to modify (e.g., 'reuse_flag').")
    parser_set_field.add_argument("field_value", type=lambda x: int(x,0), help="New field value (e.g., 0x1).")

    args = parser.parse_args()

    input_file_path = pathlib.Path(args.input_file).absolute()

    if args.command == 'print':
        try:
            print_inst(
                file_path=str(input_file_path),
                byte_offset=args.byte_offset
            )
        except Exception as e:
            logging.error(f"An error occurred: {e}")

    elif args.command == 'edit_bit':
        try:
            edit_inst_bit(
                file_path=str(input_file_path),
                byte_offset=args.byte_offset,
                bit_index=args.bit_index,
                new_bit=args.new_bit
            )
        except Exception as e:
            logging.error(f"An error occurred: {e}")

    elif args.command == 'search':
        try:
            matching_offsets = find_instructions(
                file_path=str(input_file_path),
                opcode1=args.opcode1,
                opcode2=args.opcode2,
                aligned=args.aligned
            )
            if matching_offsets:
                print(f"Found {len(matching_offsets)} matching instructions at byte offsets within .nv_fatbin section:")
                for offset in matching_offsets:
                    print(f"  {offset} (0x{offset:X})")
            else:
                print("No matching instructions found.")
        except Exception as e:
            logging.error(f"An error occurred: {e}")

    elif args.command == 'set_field':
        try:
            set_field(
                file_path=str(input_file_path),
                byte_offset=args.byte_offset,
                field_name=args.field_name,
                field_value=args.field_value
            )
        except Exception as e:
            logging.error(f"An error occurred: {e}")

    else:
        parser.print_help()

if __name__ == "__main__":
    main()
