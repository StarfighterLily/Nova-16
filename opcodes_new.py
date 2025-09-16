# Opcode table for Prefixed Operand Architecture
# Each instruction consists of:
# 1. Opcode (1 byte): Core operation
# 2. Mode byte (1 byte): Operand addressing modes
# 3. Operand data: Variable length based on modes

# Core operations only - no operand variants
# Reduced from ~200 opcodes to ~50 core operations

opcodes = [
    # No-operand instructions
    ("HLT",                "0x00", 1), # Halt execution
    ("NOP",                "0x01", 1), # No operation
    ("RET",                "0x02", 1), # Return from subroutine
    ("IRET",               "0x03", 1), # Return from interrupt
    ("CLI",                "0x04", 1), # Clear interrupt flag
    ("STI",                "0x05", 1), # Set interrupt flag

    # Data movement
    ("MOV",                "0x06", 1), # Move data between operands

    # Arithmetic operations
    ("ADD",                "0x07", 1), # Addition
    ("SUB",                "0x08", 1), # Subtraction
    ("MUL",                "0x09", 1), # Multiplication
    ("DIV",                "0x0A", 1), # Division
    ("INC",                "0x0B", 1), # Increment
    ("DEC",                "0x0C", 1), # Decrement
    ("MOD",                "0x0D", 1), # Modulo
    ("NEG",                "0x0E", 1), # Negation
    ("ABS",                "0x0F", 1), # Absolute value

    # Bitwise operations
    ("AND",                "0x10", 1), # Bitwise AND
    ("OR",                 "0x11", 1), # Bitwise OR
    ("XOR",                "0x12", 1), # Bitwise XOR
    ("NOT",                "0x13", 1), # Bitwise NOT
    ("SHL",                "0x14", 1), # Shift left
    ("SHR",                "0x15", 1), # Shift right
    ("ROL",                "0x16", 1), # Rotate left
    ("ROR",                "0x17", 1), # Rotate right

    # Stack operations
    ("PUSH",               "0x18", 1), # Push to stack
    ("POP",                "0x19", 1), # Pop from stack
    ("PUSHF",              "0x1A", 1), # Push flags
    ("POPF",               "0x1B", 1), # Pop flags
    ("PUSHA",              "0x1C", 1), # Push all registers
    ("POPA",               "0x1D", 1), # Pop all registers

    # Control flow - jumps
    ("JMP",                "0x1E", 1), # Unconditional jump
    ("JZ",                 "0x1F", 1), # Jump if zero
    ("JNZ",                "0x20", 1), # Jump if not zero
    ("JO",                 "0x21", 1), # Jump if overflow
    ("JNO",                "0x22", 1), # Jump if no overflow
    ("JC",                 "0x23", 1), # Jump if carry
    ("JNC",                "0x24", 1), # Jump if no carry
    ("JS",                 "0x25", 1), # Jump if sign
    ("JNS",                "0x26", 1), # Jump if no sign
    ("JGT",                "0x27", 1), # Jump if greater than
    ("JLT",                "0x28", 1), # Jump if less than
    ("JGE",                "0x29", 1), # Jump if greater or equal
    ("JLE",                "0x2A", 1), # Jump if less or equal

    # Control flow - branches (relative)
    ("BR",                 "0x2B", 1), # Branch (relative jump)
    ("BRZ",                "0x2C", 1), # Branch if zero
    ("BRNZ",               "0x2D", 1), # Branch if not zero

    # Comparison
    ("CMP",                "0x2E", 1), # Compare operands

    # Call
    ("CALL",               "0x2F", 1), # Call subroutine

    # Interrupt
    ("INT",                "0x30", 1), # Software interrupt

    # Graphics operations
    ("SBLEND",             "0x31", 1), # Set blend mode
    ("SREAD",              "0x32", 1), # Read screen pixel
    ("SWRITE",             "0x33", 1), # Write screen pixel
    ("SROLX",              "0x34", 1), # Rotate screen X
    ("SROLY",              "0x35", 1), # Rotate screen Y
    ("SROTL",              "0x36", 1), # Rotate screen left
    ("SROTR",              "0x37", 1), # Rotate screen right
    ("SSHFTX",             "0x38", 1), # Shift screen X
    ("SSHFTY",             "0x39", 1), # Shift screen Y
    ("SFLIPX",             "0x3A", 1), # Flip screen X
    ("SFLIPY",             "0x3B", 1), # Flip screen Y
    ("SBLIT",              "0x3C", 1), # Blit screen
    ("SFILL",              "0x3D", 1), # Fill screen

    # VRAM operations
    ("VREAD",              "0x3E", 1), # Read VRAM
    ("VWRITE",             "0x3F", 1), # Write VRAM
    ("VBLIT",              "0x40", 1), # Blit VRAM

    # Text operations
    ("CHAR",               "0x41", 1), # Draw character
    ("TEXT",               "0x42", 1), # Draw text

    # Keyboard operations
    ("KEYIN",              "0x43", 1), # Read key
    ("KEYSTAT",            "0x44", 1), # Check key status
    ("KEYCOUNT",           "0x45", 1), # Get key count
    ("KEYCLEAR",           "0x46", 1), # Clear keyboard buffer
    ("KEYCTRL",            "0x47", 1), # Keyboard control

    # Random operations
    ("RND",                "0x48", 1), # Random number
    ("RNDR",               "0x49", 1), # Random number in range

    # Memory operations
    ("MEMCPY",             "0x4A", 1), # Memory copy

    # BCD operations
    ("SED",                "0x4B", 1), # Set decimal flag
    ("CLD",                "0x4C", 1), # Clear decimal flag
    ("CLA",                "0x4D", 1), # Clear auxiliary carry
    ("BCDA",               "0x4E", 1), # BCD add with carry
    ("BCDS",               "0x4F", 1), # BCD subtract with carry
    ("BCDCMP",             "0x50", 1), # BCD compare
    ("BCD2BIN",            "0x51", 1), # BCD to binary
    ("BIN2BCD",            "0x52", 1), # Binary to BCD
    ("BCDADD",             "0x53", 1), # BCD add immediate
    ("BCDSUB",             "0x54", 1), # BCD subtract immediate

    # Sprite operations
    ("SPBLIT",             "0x55", 1), # Blit sprite
    ("SPBLITALL",          "0x56", 1), # Blit all sprites

    # Sound operations
    ("SPLAY",              "0x57", 1), # Play sound
    ("SSTOP",              "0x58", 1), # Stop sound
    ("STRIG",              "0x59", 1), # Trigger sound effect

    # Loop operation
    ("LOOP",               "0x5A", 1), # Loop instruction

    # Register/special references (for direct access)
    ("SA",                 "0x5B", 1), # Sound Address
    ("SF",                 "0x5C", 1), # Sound Frequency
    ("SV",                 "0x5D", 1), # Sound Volume
    ("SW",                 "0x5E", 1), # Sound Waveform
    ("VM",                 "0x5F", 1), # Video Mode
    ("VL",                 "0x60", 1), # Video Layer
    ("TT",                 "0x61", 1), # Timer
    ("TM",                 "0x62", 1), # Timer Match
    ("TC",                 "0x63", 1), # Timer Control
    ("TS",                 "0x64", 1), # Timer Speed
    ("R0",                 "0x65", 1),
    ("R1",                 "0x66", 1),
    ("R2",                 "0x67", 1),
    ("R3",                 "0x68", 1),
    ("R4",                 "0x69", 1),
    ("R5",                 "0x6A", 1),
    ("R6",                 "0x6B", 1),
    ("R7",                 "0x6C", 1),
    ("R8",                 "0x6D", 1),
    ("R9",                 "0x6E", 1),
    ("P0",                 "0x6F", 1),
    ("P1",                 "0x70", 1),
    ("P2",                 "0x71", 1),
    ("P3",                 "0x72", 1),
    ("P4",                 "0x73", 1),
    ("P5",                 "0x74", 1),
    ("P6",                 "0x75", 1),
    ("P7",                 "0x76", 1),
    ("P8",                 "0x77", 1),
    ("P9",                 "0x78", 1),
    ("SP",                 "0x77", 1),  # SP is P8
    ("FP",                 "0x78", 1),  # FP is P9
    ("VX",                 "0x79", 1),
    ("VY",                 "0x7A", 1),
]