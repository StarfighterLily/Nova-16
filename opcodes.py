# Opcode table for Prefixed Operand Architecture
# Each instruction consists of:
# 1. Opcode (1 byte): Core operation
# 2. Mode byte (1 byte): Operand addressing modes
# 3. Operand data: Variable length based on modes

# Core operations only - no operand variants
# Reduced from ~200 opcodes to ~50 core operations

opcodes = [
    # No-operand instructions
    ("HLT",                "0x00", 0), # Halt execution # implemented
    ("NOP",                "0xFF", 0), # No operation # implemented
    ("RET",                "0x01", 0), # Return from subroutine # implemented
    ("IRET",               "0x02", 0), # Return from interrupt # implemented
    ("CLI",                "0x03", 0), # Clear interrupt flag # implemented
    ("STI",                "0x04", 0), # Set interrupt flag # implemented

    # Data movement
    ("MOV",                "0x06", 2), # Move data between operands (variable size) # implemented

    # Arithmetic operations
    ("ADD",                "0x07", 2), # Addition # implemented
    ("SUB",                "0x08", 2), # Subtraction # implemented
    ("MUL",                "0x09", 2), # Multiplication # implemented
    ("DIV",                "0x0A", 2), # Division # implemented
    ("INC",                "0x0B", 1), # Increment # implemented
    ("DEC",                "0x0C", 1), # Decrement # implemented
    ("MOD",                "0x0D", 2), # Modulo # implemented
    ("NEG",                "0x0E", 1), # Negation # implemented
    ("ABS",                "0x0F", 1), # Absolute value # implemented

    # Bitwise operations
    ("AND",                "0x10", 2), # Bitwise AND # implemented
    ("OR",                 "0x11", 2), # Bitwise OR # implemented
    ("XOR",                "0x12", 2), # Bitwise XOR # implemented
    ("NOT",                "0x13", 1), # Bitwise NOT # implemented
    ("SHL",                "0x14", 2), # Shift left # implemented
    ("SHR",                "0x15", 2), # Shift right # implemented
    ("ROL",                "0x16", 2), # Rotate left # implemented
    ("ROR",                "0x17", 2), # Rotate right # implemented

    # Stack operations
    ("PUSH",               "0x18", 1), # Push to stack # implemented
    ("POP",                "0x19", 1), # Pop from stack # implemented
    ("PUSHF",              "0x1A", 0), # Push flags # implemented
    ("POPF",               "0x1B", 0), # Pop flags # implemented
    ("PUSHA",              "0x1C", 0), # Push all registers # implemented
    ("POPA",               "0x1D", 0), # Pop all registers # implemented

    # Control flow - jumps
    ("JMP",                "0x1E", 1), # Unconditional jump # implemented
    ("JZ",                 "0x1F", 1), # Jump if zero # implemented
    ("JNZ",                "0x20", 1), # Jump if not zero # implemented
    ("JO",                 "0x21", 1), # Jump if overflow # implemented
    ("JNO",                "0x22", 1), # Jump if no overflow # implemented
    ("JC",                 "0x23", 1), # Jump if carry # implemented
    ("JNC",                "0x24", 1), # Jump if no carry # implemented
    ("JS",                 "0x25", 1), # Jump if sign # implemented
    ("JNS",                "0x26", 1), # Jump if no sign # implemented
    ("JGT",                "0x27", 1), # Jump if greater than # implemented
    ("JLT",                "0x28", 1), # Jump if less than # implemented
    ("JGE",                "0x29", 1), # Jump if greater or equal # implemented
    ("JLE",                "0x2A", 1), # Jump if less or equal # implemented

    # Control flow - branches (relative)
    ("BR",                 "0x2B", 1), # Branch (relative jump) # implemented
    ("BRZ",                "0x2C", 1), # Branch if zero # implemented
    ("BRNZ",               "0x2D", 1), # Branch if not zero # implemented

    # Comparison
    ("CMP",                "0x2E", 2), # Compare operands # implemented

    # Call
    ("CALL",               "0x2F", 1), # Call subroutine # implemented

    # Interrupt
    ("INT",                "0x30", 1), # Software interrupt # implemented

    # Graphics operations
    ("SBLEND",             "0x31", 1), # Set blend mode # implemented
    ("SREAD",              "0x32", 1), # Read screen pixel # implemented
    ("SWRITE",             "0x33", 1), # Write screen pixel # implemented
    ("SROL",               "0x34", 2), # Roll screen by axis, amount # implemented
    ("SROT",               "0x35", 2), # Rotate screen by direction, amount # implemented
    ("SSHFT",              "0x36", 2), # Shift screen by axis, amount # implemented
    ("SFLIP",              "0x37", 2), # Flip screen by axis, amount # implemented
    ("SLINE",              "0x38", 5), # Line x1, y1, x2, y2, color # unimplemented
    ("SRECT",              "0x39", 6), # Rectangle x1, y1, x2, y2, color, un/filled # unimplemented
    ("SCIRC",              "0x3A", 5), # Circle x, y, radius, color, un/filled # unimplemented
    ("SINV",               "0x3B", 0), # Invert screen colors # unimplemented
    ("SBLIT",              "0x3C", 1), # Blit screen # implemented
    ("SFILL",              "0x3D", 1), # Fill screen # implemented

    # VRAM operations
    ("VREAD",              "0x3E", 1), # Read VRAM # implemented
    ("VWRITE",             "0x3F", 2), # Write VRAM # implemented
    ("VBLIT",              "0x40", 1), # Blit VRAM # implemented

    # Text operations
    ("CHAR",               "0x41", 2), # Draw character # implemented
    ("TEXT",               "0x42", 2), # Draw text # implemented

    # Keyboard operations
    ("KEYIN",              "0x43", 1), # Read key # implemented
    ("KEYSTAT",            "0x44", 1), # Check key status # implemented
    ("KEYCOUNT",           "0x45", 1), # Get key count # implemented
    ("KEYCLEAR",           "0x46", 1), # Clear keyboard buffer # implemented
    ("KEYCTRL",            "0x47", 1), # Keyboard control # implemented

    # Random operations
    ("RND",                "0x48", 1), # Random number # implemented
    ("RNDR",               "0x49", 3), # Random number in range destination, min, max # implemented

    # Memory operations
    ("MEMCPY",             "0x4A", 3), # Memory copy # implemented

    # BCD operations
    ("SED",                "0x4B", 1), # Set decimal flag # implemented
    ("CLD",                "0x4C", 1), # Clear decimal flag # implemented
    ("CLA",                "0x4D", 1), # Clear auxiliary carry # implemented
    ("BCDA",               "0x4E", 1), # BCD add with carry # implemented
    ("BCDS",               "0x4F", 1), # BCD subtract with carry # implemented
    ("BCDCMP",             "0x50", 1), # BCD compare # implemented
    ("BCD2BIN",            "0x51", 1), # BCD to binary # implemented
    ("BIN2BCD",            "0x52", 1), # Binary to BCD # implemented
    ("BCDADD",             "0x53", 1), # BCD add immediate # implemented
    ("BCDSUB",             "0x54", 1), # BCD subtract immediate # implemented

    # Sprite operations
    ("SPBLIT",             "0x55", 1), # Blit sprite # implemented
    ("SPBLITALL",          "0x56", 1), # Blit all sprites # implemented

    # Sound operations
    ("SPLAY",              "0x57", 0), # Play sound # implemented
    ("SSTOP",              "0x58", 0), # Stop sound # implemented
    ("STRIG",              "0x59", 1), # Trigger sound effect # implemented

    # Loop operation
    ("LOOP",               "0x5A", 2), # Loop instruction # implemented

    # Math functions
    ("POWR",               "0x5B", 2), # Power base, exponent # implemented
    ("SQRT",               "0x5C", 1), # Square value # implemented
    ("LOG",                "0x5D", 1), # Logarithm value # implemented
    ("EXP",                "0x5E", 1), # Exponential value # implemented
    ("SIN",                "0x5F", 1), # Sine value # implemented
    ("COS",                "0x60", 1), # Cosine value # implemented
    ("TAN",                "0x61", 1), # Tangent value # implemented
    ("ATAN",               "0x62", 1), # Arctangent value # implemented
    ("ASIN",               "0x63", 1), # Arcsine value # implemented
    ("ACOS",               "0x64", 1), # Arccosine value # implemented
    ("DEG",                "0x65", 1), # Degrees to radians # implemented
    ("RAD",                "0x66", 1), # Radians to degrees # implemented
    ("FLOOR",              "0x67", 1), # Floor value # implemented
    ("CEIL",               "0x68", 1), # Ceil value # implemented
    ("ROUND",              "0x69", 1), # Round value # implemented
    ("TRUNC",              "0x6A", 1), # Truncate value # implemented
    ("FRAC",               "0x6B", 1), # Fractional part # implemented
    ("INTGR",              "0x6C", 1), # Integer part # implemented

    # Bit test and modify
    ("BTST",               "0x6D", 2), # Bit test # implemented
    ("BSET",               "0x6E", 2), # Bit set # implemented
    ("BCLR",               "0x6F", 2), # Bit clear # implemented
    ("BFLIP",              "0x70", 2), # Bit flip # implemented

    # String operations
    ("STRCPY",             "0x71", 2), # String copy destination, source # implemented
    ("STRCAT",             "0x72", 2), # String concatenate destination, source # implemented
    ("STRCMP",             "0x73", 3), # String compare str1, str2, length # implemented
    ("STRLEN",             "0x74", 1), # String length # implemented
    ("STREXT",             "0x75", 4), # String extract destination, haystack, needle, length # implemented
    ("STREXTI",            "0x76", 4), # String extract case-insensitive destination, haystack, needle, length # implemented
    ("STRUPR",             "0x77", 1), # String to uppercase # implemented
    ("STRLWR",             "0x78", 1), # String to lowercase # implemented
    ("STRREV",             "0x79", 1), # String reverse # implemented
    ("STRFIND",            "0x7A", 2), # String substring exists haystack, needle # implemented
    ("STRFINDI",           "0x7B", 2), # String case-insensitive substring exists haystack, needle # implemented

    # Memory de/allocation and testing
    ("MEMSET",             "0x7C", 3), # Memory set address, value, length # unimplemented
    ("MEMTEST",            "0x7D", 3), # Memory test addr1, addr2, length # unimplemented
    ("MEMMOVE",            "0x7E", 3), # Memory move destination, source, length # unimplemented

    # Sound Enhancements
    ("SMIX",               "0x7F", 1), # Mix channels output, in1, in2 # unimplemented
    ("SECHO",              "0x80", 2), # Echo channel, delay # unimplemented
    ("SREVERB",            "0x81", 2), # Reverb channel, amount # unimplemented
    ("SFILTER",            "0x82", 2), # Filter channel, type # unimplemented

    # Layer operations
    ("LCPY",               "0x83", 2), # Copy contents of layer dest, source # unimplemented
    ("LCLR",               "0x84", 1), # Clear layer to color # unimplemented
    ("LMOV",               "0x85", 2), # Move contents of layer dest, source # unimplemented
    ("LSHFT",              "0x86", 2), # Shift layer by axis, amount # unimplemented
    ("LROT",               "0x87", 2), # Rotate layer by direction, amount # unimplemented
    ("LFLIP",              "0x88", 2), # Flip layer by axis, amount # unimplemented
    ("LSWAP",              "0x89", 2), # Swap two layers dest, source # unimplemented

    # 

    # Register/special references (for direct access)
    ("SA",                 "0xDD", 1), # Sound Address
    ("SF",                 "0xDE", 1), # Sound Frequency
    ("SV",                 "0xDF", 1), # Sound Volume
    ("SW",                 "0xE0", 1), # Sound Waveform
    ("VM",                 "0xE1", 1), # Video Mode
    ("VL",                 "0xE2", 1), # Video Layer
    ("TT",                 "0xE3", 1), # Timer
    ("TM",                 "0xE4", 1), # Timer Match
    ("TC",                 "0xE5", 1), # Timer Control
    ("TS",                 "0xE6", 1), # Timer Speed
    ("R0",                 "0xE7", 1),
    ("R1",                 "0xE8", 1),
    ("R2",                 "0xE9", 1),
    ("R3",                 "0xEA", 1),
    ("R4",                 "0xEB", 1),
    ("R5",                 "0xEC", 1),
    ("R6",                 "0xED", 1),
    ("R7",                 "0xEE", 1),
    ("R8",                 "0xEF", 1),
    ("R9",                 "0xF0", 1),
    ("P0",                 "0xF1", 1),
    ("P1",                 "0xF2", 1),
    ("P2",                 "0xF3", 1),
    ("P3",                 "0xF4", 1),
    ("P4",                 "0xF5", 1),
    ("P5",                 "0xF6", 1),
    ("P6",                 "0xF7", 1),
    ("P7",                 "0xF8", 1),
    ("P8",                 "0xF9", 1),
    ("P9",                 "0xFA", 1),
    ("SP",                 "0xFB", 1),  # SP is P8
    ("FP",                 "0xFC", 1),  # FP is P9
    ("VX",                 "0xFD", 1),
    ("VY",                 "0xFE", 1),
    # P regi
    ("P0:",                "0xC9", 1), # P0 high byte
    ("P1:",                "0xCA", 1), # P1 high byte
    ("P2:",                "0xCB", 1), # P2 high byte
    ("P3:",                "0xCC", 1), # P3 high byte
    ("P4:",                "0xCD", 1), # P4 high byte
    ("P5:",                "0xCE", 1), # P5 high byte
    ("P6:",                "0xCF", 1), # P6 high byte
    ("P7:",                "0xD0", 1), # P7 high byte
    ("P8:",                "0xD1", 1), # P8 high byte
    ("P9:",                "0xD2", 1), # P9 high byte
    (":P0",                "0xD3", 1), # P0 low byte
    (":P1",                "0xD4", 1), # P1 low byte
    (":P2",                "0xD5", 1), # P2 low byte
    (":P3",                "0xD6", 1), # P3 low byte
    (":P4",                "0xD7", 1), # P4 low byte
    (":P5",                "0xD8", 1), # P5 low byte
    (":P6",                "0xD9", 1), # P6 low byte
    (":P7",                "0xDA", 1), # P7 low byte
    (":P8",                "0xDB", 1), # P8 low byte
    (":P9",                "0xDC", 1), # P9 low byte
]