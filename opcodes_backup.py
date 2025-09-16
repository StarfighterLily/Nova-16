# Opcode table
# Each instruction is 1 byte
# Each register is 1 byte
# Each imm8 value is 1 byte
# each imm16 value is 2 bytes
# Each address is 2 bytes

# Size is the number of bytes the instruction takes plus the number of bytes each operand takes
# For example, MOV reg reg takes 3 bytes (1 for the opcode, 2 for the registers)
# MOV reg imm8 takes 3 bytes (1 for the opcode, 1 for the register, 1 for the immediate value)
# MOV reg imm16 takes 4 bytes (1 for the opcode, 1 for the register, 2 for the immediate value)
# MOV reg regIndir takes 3 bytes (1 for the opcode, 1 for the register, 1 for the indirect address)
# MOV reg regIndex takes 3 bytes (1 for the opcode, 1 for the register, 1 for the index register)

# Proposed additions:
# 
# 

opcodes = [
    # No-operand instructions
    ("HLT",                "0x00", 1), # implemented
    ("NOP",                "0xFF", 1), # implemented
    ("RET",                "0x01", 1), # implemented
    ("IRET",               "0x02", 1), # implemented
    ("CLI",                "0x03", 1), # implemented
    ("STI",                "0x04", 1), # implemented

    # MOV variants
    ("MOV reg reg",        "0x05", 3), # implemented
    ("MOV reg imm8",       "0x06", 3), # implemented
    ("MOV reg imm16",      "0x07", 4), # implemented
    ("MOV reg regIndir",   "0x08", 3), # implemented
    ("MOV reg regIndex",   "0x09", 4), # implemented
    ("MOV regIndir reg",   "0x0A", 3), # implemented
    ("MOV regIndex reg",   "0x0B", 4), # implemented
    ("MOV regIndir imm8",  "0x0C", 3), # implemented
    ("MOV regIndex imm8",  "0x0D", 4), # implemented
    ("MOV regIndir imm16", "0x0E", 4), # implemented
    ("MOV regIndex imm16", "0x0F", 5), # implemented

    # Direct memory access MOV instructions
    ("MOV reg direct",       "0x10", 4), # load from direct memory address
    ("MOV direct reg",       "0x11", 4), # store to direct memory address

    # Arithmetic
    ("INC reg",            "0x12", 2), # implemented
    ("DEC reg",            "0x13", 2), # implemented
    ("ADD reg reg",        "0x14", 3), # implemented
    ("ADD reg imm8",       "0x15", 3), # implemented
    ("ADD reg imm16",      "0x16", 4), # implemented
    ("SUB reg reg",        "0x17", 3), # implemented
    ("SUB reg imm8",       "0x18", 3), # implemented
    ("SUB reg imm16",      "0x19", 4), # implemented
    ("MUL reg reg",        "0x1A", 3), # implemented
    ("MUL reg imm8",       "0x1B", 3), # implemented
    ("MUL reg imm16",      "0x1C", 4), # implemented
    ("DIV reg reg",        "0x1D", 3), # implemented
    ("DIV reg imm8",       "0x1E", 3), # implemented
    ("DIV reg imm16",      "0x1F", 4), # implemented

    # Bitwise
    ("AND reg reg",        "0x20", 3), # implemented
    ("AND reg imm8",       "0x21", 3), # implemented
    ("AND reg imm16",      "0x22", 4), # implemented
    ("OR reg reg",         "0x23", 3), # implemented
    ("OR reg imm8",        "0x24", 3), # implemented
    ("OR reg imm16",       "0x25", 4), # implemented
    ("XOR reg reg",        "0x26", 3), # implemented
    ("XOR reg imm8",       "0x27", 3), # implemented
    ("XOR reg imm16",      "0x28", 4), # implemented
    ("NOT reg",            "0x29", 2), # implemented
    ("SHL reg",            "0x2A", 2), # implemented
    ("SHR reg",            "0x2B", 2), # implemented
    ("ROL reg",            "0x2C", 2), # implemented
    ("ROR reg",            "0x2D", 2), # implemented

    # Stack
    ("PUSH reg",           "0x2E", 2), # implemented
    ("POP reg",            "0x2F", 2), # implemented
    ("PUSHF",              "0x30", 1), # implemented
    ("POPF",               "0x31", 1), # implemented
    ("PUSHA",              "0x32", 1), # implemented
    ("POPA",               "0x33", 1), # implemented

    # Control flow - jumps
    ("JMP imm16",          "0x34", 3), # implemented
    ("JMP reg",            "0x35", 3), # implemented
    ("JZ imm16",           "0x36", 3), # implemented
    ("JZ reg",             "0x37", 3), # implemented
    ("JNZ imm16",          "0x38", 3), # implemented
    ("JNZ reg",            "0x39", 3), # implemented
    ("JO imm16",           "0x3A", 3), # implemented
    ("JO reg",             "0x3B", 3), # implemented
    ("JNO imm16",          "0x3C", 3), # implemented
    ("JNO reg",            "0x3D", 3), # implemented
    ("JC imm16",           "0x3E", 3), # implemented
    ("JC reg",             "0x3F", 3), # implemented
    ("JNC imm16",          "0x40", 3), # implemented
    ("JNC reg",            "0x41", 3), # implemented
    ("JS imm16",           "0x42", 3), # implemented
    ("JS reg",             "0x43", 3), # implemented
    ("JNS imm16",          "0x44", 3), # implemented
    ("JNS reg",            "0x45", 3), # implemented

    # Control flow - branches (relative jumping forward and backward)
    ("BR imm8",            "0x46", 2), # implemented
    ("BR reg",             "0x47", 2), # implemented
    ("BRZ imm8",           "0x48", 2), # implemented
    ("BRZ reg",            "0x49", 2), # implemented
    ("BRNZ imm8",          "0x4A", 2), # implemented
    ("BRNZ reg",           "0x4B", 2), # implemented

    # Interrupt calls
    ("INT imm8",           "0x4C", 2), # implemented
    ("INT reg",            "0x4D", 2), # implemented
    
    # Graphics Blending Instructions
    # Set blend mode (0=normal, 1=add, 2=sub, 3=mult, 4=screen)
    ("SBLEND imm8",        "0x4E", 2), # implemented
    # Set blend mode with alpha/intensity (mode, alpha 0-255)
    ("SBLEND imm8 imm8",   "0x4F", 3), # implemented

    # Screen manipulation
    ("SREAD reg",          "0x50", 2), # implemented
    ("SWRITE reg",         "0x51", 2), # implemented
    ("SWRITE imm16",       "0x52", 3), # implemented
    ("SROLX reg",          "0x53", 2), # implemented
    ("SROLX imm8",         "0x54", 2), # implemented
    ("SROLY reg",          "0x55", 2), # implemented
    ("SROLY imm8",         "0x56", 2), # implemented
    ("SROTL reg",          "0x57", 2), # implemented
    ("SROTL imm8",         "0x58", 2), # implemented
    ("SROTR reg",          "0x59", 2), # implemented
    ("SROTR imm8",         "0x5A", 2), # implemented
    ("SSHFTX reg",         "0x5B", 2), # implemented
    ("SSHFTX imm8",        "0x5C", 2), # implemented
    ("SSHFTY reg",         "0x5D", 2), # implemented
    ("SSHFTY imm8",        "0x5E", 2), # implemented
    ("SFLIPX",             "0x5F", 1), # implemented
    ("SFLIPY",             "0x60", 1), # implemented
    ("SBLIT",              "0x61", 1), # implemented

    # Comparison
    ("CMP reg reg",        "0x62", 3), # implemented
    ("CMP reg imm8",       "0x63", 3), # implemented
    ("CMP reg imm16",      "0x64", 4), # implemented

    # VRAM
    ("VREAD reg",          "0x65", 2), # implemented
    ("VWRITE reg",         "0x66", 2), # implemented
    ("VWRITE imm16",       "0x67", 3), # implemented
    ("VBLIT",              "0x68", 1), # implemented

    # CALL
    ("CALL imm16",         "0x69", 3), # implemented

    # Text/Character instructions
    ("CHAR reg imm8",      "0x6A", 3), # implemented
    ("TEXT reg imm8",      "0x6B", 3), # implemented
    ("TEXT imm16 imm8",    "0x6C", 4), # implemented
    ("CHAR reg reg",       "0x6D", 3), # implemented
    ("TEXT reg reg",       "0x6E", 3), # implemented
    ("TEXT imm16 reg",     "0x6F", 4), # implemented

    # Control flow, 2
    ("JGT imm16",          "0x70", 3), # implemented
    ("JLT imm16",          "0x71", 3), # implemented
    ("JGE imm16",          "0x72", 3), # implemented
    ("JLE imm16",          "0x73", 3), # implemented

    # Keyboard I/O instructions
    ("KEYIN reg",          "0x74", 2), # implemented
    ("KEYSTAT reg",        "0x75", 2), # implemented
    ("KEYCOUNT reg",       "0x76", 2), # implemented
    ("KEYCLEAR",           "0x77", 1), # implemented
    ("KEYCTRL reg",        "0x78", 2), # implemented
    ("KEYCTRL imm8",       "0x79", 2), # implemented

    # Misc
    # modulo
    ("MOD reg reg",        "0x7A", 3), # implemented
    ("MOD reg imm8",       "0x7B", 3), # implemented
    ("MOD reg imm16",      "0x7C", 4), # implemented
    # negation, absolute value
    ("NEG reg",            "0x7D", 2), # implemented
    ("ABS reg",            "0x7E", 2), # implemented
    # screen fill - fill whole screen with value
    ("SFILL reg",          "0x7F", 2), # implemented
    ("SFILL imm8",         "0x80", 2), # implemented
    # loop: decrement from value and jump at 0
    ("LOOP reg reg",       "0x81", 3), # implemented
    ("LOOP imm8 reg",      "0x82", 3), # implemented
    # random number 0-65535 stored to reg (low byte only if stored to 8 bit reg)
    ("RND reg",            "0x83", 2), # implemented
    # random number stored to reg from lower bound to upper bound
    ("RNDR reg reg reg",   "0x84", 4), # dest + lower_bound_reg + upper_bound_reg 
    ("RNDR reg imm8 imm8", "0x85", 4), # dest + lower_bound_imm8 + upper_bound_imm8
    ("RNDR reg imm16 imm16","0x86",6), # dest + lower_bound_imm16 + upper_bound_imm16
    # Memory copy to reg from reg with val bytes
    ("MEMCPY reg reg reg", "0x87", 4), # implemented
    ("MEMCPY reg reg imm8","0x88", 4), # implemented
    ("MEMCPY reg reg imm16","0x89",5), # implemented

    # BCD (Binary Coded Decimal) Instructions
    ("SED",                "0x8A", 1), # Set decimal flag (enable BCD mode)
    ("CLD",                "0x8B", 1), # Clear decimal flag (disable BCD mode)
    ("CLA",                "0x8C", 1), # Clear BCD auxiliary carry flag
    ("BCDA reg reg",       "0x8D", 3), # BCD add with auxiliary carry
    ("BCDS reg reg",       "0x8E", 3), # BCD subtract with auxiliary carry
    ("BCDCMP reg reg",     "0x8F", 3), # BCD compare (sets flags without storing result)
    ("BCD2BIN reg",        "0x90", 2), # Convert BCD to binary in register
    ("BIN2BCD reg",        "0x91", 2), # Convert binary to BCD in register
    ("BCDADD reg imm8",    "0x92", 3), # BCD add immediate
    ("BCDSUB reg imm8",    "0x93", 3), # BCD subtract immediate

    # Sprite Instructions
    ("SPBLIT reg",         "0x94", 2), # Blit specific sprite by ID (0-15)
    ("SPBLIT imm8",        "0x95", 2), # Blit specific sprite by ID (0-15)
    ("SPBLITALL",          "0x96", 1), # Blit all active sprites
    
    # Sound Instructions
    ("SPLAY",              "0x97", 1), # Start playing sound using current sound registers
    ("SPLAY reg",          "0x98", 2), # Start playing sound on specific channel
    ("SSTOP",              "0x99", 1), # Stop all sound channels
    ("SSTOP reg",          "0x9A", 2), # Stop specific sound channel
    ("STRIG",              "0x9B", 1), # Trigger sound effect (type from SW register)
    ("STRIG imm8",         "0x9C", 2), # Trigger specific sound effect type
    
#     - - - Register section - - - 

    # Sound registers
    ("SA",                 "0x9D", 1), # Sound Address (16-bit)
    ("SF",                 "0x9E", 1), # Sound Frequency (8-bit)
    ("SV",                 "0x9F", 1), # Sound Volume (8-bit)
    ("SW",                 "0xA0", 1), # Sound Waveform/Control (8-bit)
    ("SA:",                "0xA1", 1), # Sound Address high byte
    (":SA",                "0xA2", 1), # Sound Address low byte

    # Video Mode register (direct only)
    ("VM",                 "0xA3", 1),
    # Video layer register (direct only)
    # 1-4 = BG Layer n, 5-8 = Sprite Layer n
    # Any screen-writing operation will take place on the VL layer specified
    ("VL",                 "0xA4", 1),

    # Timer control registers
    ("TT",                 "0xA5", 1),
    ("TM",                 "0xA6", 1),
    ("TC",                 "0xA7", 1),
    ("TS",                 "0xA8", 1),

    # Registers, direct
    ("R0",                 "0xA9", 1),
    ("R1",                 "0xAA", 1),
    ("R2",                 "0xAB", 1),
    ("R3",                 "0xAC", 1),
    ("R4",                 "0xAD", 1),
    ("R5",                 "0xAE", 1),
    ("R6",                 "0xAF", 1),
    ("R7",                 "0xB0", 1),
    ("R8",                 "0xB1", 1),
    ("R9",                 "0xB2", 1),
    ("P0",                 "0xB3", 1),
    ("P1",                 "0xB4", 1),
    ("P2",                 "0xB5", 1),
    ("P3",                 "0xB6", 1),
    ("P4",                 "0xB7", 1),
    ("P5",                 "0xB8", 1),
    ("P6",                 "0xB9", 1),
    ("P7",                 "0xBA", 1),
    ("P8",                 "0xBB", 1),
    ("P9",                 "0xBC", 1),
    ("SP",                 "0xBB", 1),  # SP is P8
    ("FP",                 "0xBC", 1),  # FP is P9
    ("VX",                 "0xBD", 1),
    ("VY",                 "0xBE", 1),

    # Registers, indirect
    ("R0",                 "0xBF", 1),
    ("R1",                 "0xC0", 1),
    ("R2",                 "0xC1", 1),
    ("R3",                 "0xC2", 1),
    ("R4",                 "0xC3", 1),
    ("R5",                 "0xC4", 1),
    ("R6",                 "0xC5", 1),
    ("R7",                 "0xC6", 1),
    ("R8",                 "0xC7", 1),
    ("R9",                 "0xC8", 1),
    ("P0",                 "0xC9", 1),
    ("P1",                 "0xCA", 1),
    ("P2",                 "0xCB", 1),
    ("P3",                 "0xCC", 1),
    ("P4",                 "0xCD", 1),
    ("P5",                 "0xCE", 1),
    ("P6",                 "0xCF", 1),
    ("P7",                 "0xD0", 1),
    ("P8",                 "0xD1", 1),
    ("P9",                 "0xD2", 1),
    ("SP",                 "0xD1", 1),  # SP indirect is P8 indirect
    ("FP",                 "0xD2", 1),  # FP indirect is P9 indirect
    ("VX",                 "0xD3", 1),
    ("VY",                 "0xD4", 1),

    # High byte
    ("P0:",                "0xD5", 1),
    ("P1:",                "0xD6", 1),
    ("P2:",                "0xD7", 1),
    ("P3:",                "0xD8", 1),
    ("P4:",                "0xD9", 1),
    ("P5:",                "0xDA", 1),
    ("P6:",                "0xDB", 1),
    ("P7:",                "0xDC", 1),
    ("P8:",                "0xDD", 1),
    ("P9:",                "0xDE", 1),
    ("SP:",                "0xDD", 1),  # SP high byte is P8 high byte
    ("FP:",                "0xDE", 1),  # FP high byte is P9 high byte

    # Low byte
    (":P0",                "0xDF", 1),
    (":P1",                "0xE0", 1),
    (":P2",                "0xE1", 1),
    (":P3",                "0xE2", 1),
    (":P4",                "0xE3", 1),
    (":P5",                "0xE4", 1),
    (":P6",                "0xE5", 1),
    (":P7",                "0xE6", 1),
    (":P8",                "0xE7", 1),
    (":P9",                "0xE8", 1),
    (":SP",                "0xE7", 1),  # SP low byte is P8 low byte
    (":FP",                "0xE8", 1),  # FP low byte is P9 low byte

    # Indexed
    ("R0",                 "0xE9", 1),
    ("R1",                 "0xEA", 1),
    ("R2",                 "0xEB", 1),
    ("R3",                 "0xEC", 1),
    ("R4",                 "0xED", 1),
    ("R5",                 "0xEE", 1),
    ("R6",                 "0xEF", 1),
    ("R7",                 "0xF0", 1),
    ("R8",                 "0xF1", 1),
    ("R9",                 "0xF2", 1),
    ("P0",                 "0xF3", 1),
    ("P1",                 "0xF4", 1),
    ("P2",                 "0xF5", 1),
    ("P3",                 "0xF6", 1),
    ("P4",                 "0xF7", 1),
    ("P5",                 "0xF8", 1),
    ("P6",                 "0xF9", 1),
    ("P7",                 "0xFA", 1),
    ("P8",                 "0xFB", 1),
    ("P9",                 "0xFC", 1),
    ("SP",                 "0xFB", 1),  # SP indexed is P8 indexed
    ("FP",                 "0xFC", 1),  # FP indexed is P9 indexed
    ("VX",                 "0xFD", 1),
    ("VY",                 "0xFE", 1),
]