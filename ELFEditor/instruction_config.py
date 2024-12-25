# instruction_config.py

COMMON_FIELDS = {
    "opcode1": (0, 15),       # 位 0-15
    "opcode2": (72, 87),      # 位 72-87
    "control_code": (105, 121),  # 位 105-121
    "stall_count": (105, 108),  # 位 105-108
    "yield_flag": (109, 109),  # 位 109
    "write_barrier": (110, 112),  # 位 110-112
    "read_barrier": (113, 115),  # 位 113-115
    "wait_barrier": (116, 121),  # 位 116-121
    "rd": (16, 23),  # 位 16-23
    "rs1": (24, 31),  # 位 24-31
    "rs2": (32, 39),  # 位 32-39
    "rs3": (64, 71),  # 位 64-71
}

INSTRUCTION_TYPES = [
    # {
    #     "name": "HMMA.SP",
    #     "opcode1": 0x1234,  # 替换为 HMMA.SP 的实际 opcode1 值
    #     "opcode2": 0xABCD,  # 替换为 HMMA.SP 的实际 opcode2 值
    #     "fields": {
    #         "reuse_flag": (130, 133)  # 替换为 HMMA.SP 中 reuse_flag 实际位位置
    #     }
    # },
    # {
    #     "name": "TEXS",
    #     "opcode1": 0x5678,  # 替换为 TEXS 的实际 opcode1 值
    #     "opcode2": 0xEF01,  # 替换为 TEXS 的实际 opcode2 值
    #     "fields": {
    #         "reuse_flag": (140, 143)  # 替换为 TEXS 中 reuse_flag 实际位位置
    #     }
    # },
    # 添加其他具体指令类型...
    {
        "name": "Standard",
        "opcode1": None,  # 默认类型，不基于 opcode1 匹配
        "opcode2": None,  # 默认类型，不基于 opcode2 匹配
        "fields": {
            "reuse_flag": (122, 125),
            "reuse_rs1": (122, 122),
            "reuse_rs2": (123, 123),
        }
    }
]
