# Nova-16 Instruction Set Reference

This document provides a compact reference for the Nova-16 instruction set. Instructions are organized by category. Each entry includes the instruction name, opcode (in hexadecimal), number of operands, brief description, operand expectations, and side effects.

## No-Operand Instructions
- **HLT** (0x00): 0 operands - Halt execution
  - Operands: None
  - Side Effects: Halts CPU execution
- **NOP** (0xFF): 0 operands - No operation
  - Operands: None
  - Side Effects: None
- **RET** (0x01): 0 operands - Return from subroutine
  - Operands: None
  - Side Effects: Pops return address from stack to PC
- **IRET** (0x02): 0 operands - Return from interrupt
  - Operands: None
  - Side Effects: Restores PC and flags from stack, enables interrupts
- **CLI** (0x03): 0 operands - Clear interrupt flag
  - Operands: None
  - Side Effects: Clears interrupt flag (I)
- **STI** (0x04): 0 operands - Set interrupt flag
  - Operands: None
  - Side Effects: Sets interrupt flag (I)

## Data Movement
- **MOV** (0x06): 2 operands - Move data between operands
  - Operands: dest (register/memory), src (register/memory/immediate)
  - Side Effects: Modifies dest, no flags
- **SWAP** (0x94): 1 operand - Swap nibbles
  - Operands: value (register/memory)
  - Side Effects: Swaps high and low nibbles in operand, no flags
- **XCHNG** (0x95): 2 operands - Exchange operands
  - Operands: op1, op2 (registers/memory)
  - Side Effects: Swaps values, no flags
- **MOVZ** (0x96): 2 operands - Move if zero
  - Operands: dest, src
  - Side Effects: Moves only if Z flag set, no flags changed
- **MOVNZ** (0x97): 2 operands - Move if not zero
  - Operands: dest, src
  - Side Effects: Moves only if Z flag clear, no flags changed
- **LEA** (0x98): 2 operands - Load effective address
  - Operands: dest, src (address expression)
  - Side Effects: Loads address into dest, no flags

## Arithmetic Operations
- **ADD** (0x07): 2 operands - Addition
  - Operands: dest, src
  - Side Effects: dest = dest + src, sets Z, C, S, O flags
- **SUB** (0x08): 2 operands - Subtraction
  - Operands: dest, src
  - Side Effects: dest = dest - src, sets Z, C, S, O flags
- **MUL** (0x09): 2 operands - Multiplication
  - Operands: dest, src
  - Side Effects: dest = dest * src, sets Z, C, S, O flags
- **DIV** (0x0A): 2 operands - Division
  - Operands: dest, src
  - Side Effects: dest = dest / src, sets Z, C, S, O flags
- **INC** (0x0B): 1 operand - Increment
  - Operands: dest
  - Side Effects: dest += 1, sets Z, C, S, O flags
- **DEC** (0x0C): 1 operand - Decrement
  - Operands: dest
  - Side Effects: dest -= 1, sets Z, C, S, O flags
- **MOD** (0x0D): 2 operands - Modulo
  - Operands: dest, src
  - Side Effects: dest = dest % src, sets Z, C, S, O flags
- **NEG** (0x0E): 1 operand - Negation
  - Operands: dest
  - Side Effects: dest = -dest, sets Z, C, S, O flags
- **ABS** (0x0F): 1 operand - Absolute value
  - Operands: dest
  - Side Effects: dest = |dest|, sets Z, C, S, O flags

- **ADC** (0x87): 2 operands - Add with carry
  - Operands: dest, src
  - Side Effects: dest = dest + src + C, sets Z, C, S, O flags

## Fixed-Point Arithmetic Operations (Q8.8)
- **FMUL** (0xAC): 2 operands - Fixed-point multiplication
  - Operands: dest, src
  - Side Effects: dest = (dest * src) >> 8, sets Z, C, S, O flags
- **FDIV** (0xAD): 2 operands - Fixed-point division
  - Operands: dest, src
  - Side Effects: dest = (dest << 8) / src, sets Z, C, S, O flags
- **FTOI** (0xAE): 1 operand - Fixed to integer
  - Operands: dest
  - Side Effects: dest = dest >> 8, sets Z, C, S, O flags
- **ITOF** (0xAF): 1 operand - Integer to fixed
  - Operands: dest
  - Side Effects: dest = dest << 8, sets Z, C, S, O flags

## Enhanced Arithmetic Operations
- **SBC** (0x88): 2 operands - Subtract with carry
  - Operands: dest, src
  - Side Effects: dest = dest - src - C, sets Z, C, S, O flags
- **MULH** (0x89): 2 operands - Multiply high
  - Operands: dest, src
  - Side Effects: dest = (dest * src) >> 16, sets Z, C, S, O flags
- **DIVH** (0x8A): 2 operands - Divide high
  - Operands: dest, src
  - Side Effects: dest = (dest << 16) / src, sets Z, C, S, O flags
- **MIN** (0x8B): 2 operands - Minimum
  - Operands: dest, src
  - Side Effects: dest = min(dest, src), sets Z, C, S, O flags
- **MAX** (0x8C): 2 operands - Maximum
  - Operands: dest, src
  - Side Effects: dest = max(dest, src), sets Z, C, S, O flags
- **CLZ** (0x8D): 1 operand - Count leading zeros
  - Operands: dest
  - Side Effects: dest = count of leading zeros, sets Z, C, S, O flags
- **CTZ** (0x8E): 1 operand - Count trailing zeros
  - Operands: dest
  - Side Effects: dest = count of trailing zeros, sets Z, C, S, O flags
- **POPCNT** (0x8F): 1 operand - Population count
  - Operands: dest
  - Side Effects: dest = count of set bits, sets Z, C, S, O flags

## Serial Operations
- **SERIN** (0xA2): 1 operand - Read serial data
  - Operands: dest
  - Side Effects: Reads serial data to dest
- **SEROUT** (0xA3): 1 operand - Write serial data
  - Operands: value
  - Side Effects: Writes value to serial port
- **SERSTAT** (0xA4): 1 operand - Check serial status
  - Operands: dest
  - Side Effects: Sets dest to serial status
- **SERCTRL** (0xA5): 1 operand - Serial control
  - Operands: value
  - Side Effects: Sets serial control flags

## Hardware Debugging Operations
- **SETBP** (0xA6): 2 operands - Set hardware breakpoint
  - Operands: address, index
  - Side Effects: Sets breakpoint at address
- **CLRBP** (0xA7): 1 operand - Clear hardware breakpoint
  - Operands: index
  - Side Effects: Clears breakpoint at index
- **ENABRK** (0xA8): 0 operands - Enable all hardware breakpoints
  - Operands: None
  - Side Effects: Enables all breakpoints
- **DISBRK** (0xA9): 0 operands - Disable all hardware breakpoints
  - Operands: None
  - Side Effects: Disables all breakpoints
- **ENATRAP** (0xAA): 0 operands - Enable single-step trap
  - Operands: None
  - Side Effects: Enables single-step trap
- **DISATRAP** (0xAB): 0 operands - Disable single-step trap
  - Operands: None
  - Side Effects: Disables single-step trap

## Layer Operations
- **LSWAP** (0xB0): 1 operand - Switch current layer contents with specified layer
  - Operands: layer_id
  - Side Effects: Swaps contents
- **LMOVE** (0xB1): 1 operand - Move current layer contents to specified layer, clear current layer
  - Operands: layer_id
  - Side Effects: Moves contents
- **LCOPY** (0xB2): 1 operand - Copy current layer contents to specified layer, keep current layer
  - Operands: layer_id
  - Side Effects: Copies contents

## Mouse Control
- **MOUSECTRL** (0xB3): 1 operand - Enable/disable host mouse input and interrupts
  - Operands: value
  - Side Effects: Controls mouse input/interrupts

## Bitwise Operations
- **AND** (0x10): 2 operands - Bitwise AND
  - Operands: dest, src
  - Side Effects: dest = dest & src, sets Z, C, S, O flags
- **OR** (0x11): 2 operands - Bitwise OR
  - Operands: dest, src
  - Side Effects: dest = dest | src, sets Z, C, S, O flags
- **XOR** (0x12): 2 operands - Bitwise XOR
  - Operands: dest, src
  - Side Effects: dest = dest ^ src, sets Z, C, S, O flags
- **NOT** (0x13): 1 operand - Bitwise NOT
  - Operands: dest
  - Side Effects: dest = ~dest, sets Z, C, S, O flags
- **SHL** (0x14): 2 operands - Shift left
  - Operands: dest, count
  - Side Effects: dest <<= count, sets Z, C, S, O flags
- **SHR** (0x15): 2 operands - Shift right
  - Operands: dest, count
  - Side Effects: dest >>= count, sets Z, C, S, O flags
- **ROL** (0x16): 2 operands - Rotate left
  - Operands: dest, count
  - Side Effects: dest rotated left, sets Z, C, S, O flags
- **ROR** (0x17): 2 operands - Rotate right
  - Operands: dest, count
  - Side Effects: dest rotated right, sets Z, C, S, O flags
- **SAR** (0x90): 2 operands - Shift arithmetic right
  - Operands: dest, count
  - Side Effects: dest >>= count (arithmetic), sets Z, C, S, O flags
- **SAL** (0x91): 2 operands - Shift arithmetic left
  - Operands: dest, count
  - Side Effects: dest <<= count, sets Z, C, S, O flags
- **RCL** (0x92): 2 operands - Rotate through carry left
  - Operands: dest, count
  - Side Effects: Rotate left through carry, sets Z, C, S, O flags
- **RCR** (0x93): 2 operands - Rotate through carry right
  - Operands: dest, count
  - Side Effects: Rotate right through carry, sets Z, C, S, O flags

## Bit Test and Modify
- **BTST** (0x6D): 2 operands - Bit test
  - Operands: value, bit_pos
  - Side Effects: Sets Z flag if bit clear, no other changes
- **BSET** (0x6E): 2 operands - Bit set
  - Operands: value, bit_pos
  - Side Effects: Sets bit in value, no flags
- **BCLR** (0x6F): 2 operands - Bit clear
  - Operands: value, bit_pos
  - Side Effects: Clears bit in value, no flags
- **BFLIP** (0x70): 2 operands - Bit flip
  - Operands: value, bit_pos
  - Side Effects: Flips bit in value, no flags

## Stack Operations
- **PUSH** (0x18): 1 operand - Push to stack
  - Operands: value
  - Side Effects: Pushes value to stack, SP -= 2
- **POP** (0x19): 1 operand - Pop from stack
  - Operands: dest
  - Side Effects: Pops value to dest, SP += 2
- **PUSHF** (0x1A): 0 operands - Push flags
  - Operands: None
  - Side Effects: Pushes flags to stack, SP -= 2
- **POPF** (0x1B): 0 operands - Pop flags
  - Operands: None
  - Side Effects: Pops flags from stack, SP += 2
- **PUSHA** (0x1C): 0 operands - Push all registers
  - Operands: None
  - Side Effects: Pushes all registers to stack, SP -= 40
- **POPA** (0x1D): 0 operands - Pop all registers
  - Operands: None
  - Side Effects: Pops all registers from stack, SP += 40
- **ENTER** (0x9B): 1 operand - Enter subroutine (stack frame)
  - Operands: frame_size
  - Side Effects: Sets up stack frame, pushes FP, FP = SP, SP -= frame_size
- **LEAVE** (0x9C): 0 operands - Leave subroutine (stack frame)
  - Operands: None
  - Side Effects: SP = FP, pops FP

## Control Flow - Jumps
- **JMP** (0x1E): 1 operand - Unconditional jump
  - Operands: target
  - Side Effects: PC = target
- **JZ** (0x1F): 1 operand - Jump if zero
  - Operands: target
  - Side Effects: PC = target if Z set
- **JNZ** (0x20): 1 operand - Jump if not zero
  - Operands: target
  - Side Effects: PC = target if Z clear
- **JO** (0x21): 1 operand - Jump if overflow
  - Operands: target
  - Side Effects: PC = target if O set
- **JNO** (0x22): 1 operand - Jump if no overflow
  - Operands: target
  - Side Effects: PC = target if O clear
- **JC** (0x23): 1 operand - Jump if carry
  - Operands: target
  - Side Effects: PC = target if C set
- **JNC** (0x24): 1 operand - Jump if no carry
  - Operands: target
  - Side Effects: PC = target if C clear
- **JS** (0x25): 1 operand - Jump if sign
  - Operands: target
  - Side Effects: PC = target if S set
- **JNS** (0x26): 1 operand - Jump if no sign
  - Operands: target
  - Side Effects: PC = target if S clear
- **JGT** (0x27): 1 operand - Jump if greater than
  - Operands: target
  - Side Effects: PC = target if (S == O) and Z clear
- **JLT** (0x28): 1 operand - Jump if less than
  - Operands: target
  - Side Effects: PC = target if S != O
- **JGE** (0x29): 1 operand - Jump if greater or equal
  - Operands: target
  - Side Effects: PC = target if (S == O)
- **JLE** (0x2A): 1 operand - Jump if less or equal
  - Operands: target
  - Side Effects: PC = target if (S != O) or Z set

## Control Flow - Branches (Relative)
- **BR** (0x2B): 1 operand - Branch (relative jump)
  - Operands: offset
  - Side Effects: PC += offset
- **BRZ** (0x2C): 1 operand - Branch if zero
  - Operands: offset
  - Side Effects: PC += offset if Z set
- **BRNZ** (0x2D): 1 operand - Branch if not zero
  - Operands: offset
  - Side Effects: PC += offset if Z clear

## Comparison and Call
- **CMP** (0x2E): 2 operands - Compare operands
  - Operands: op1, op2
  - Side Effects: Sets Z, C, S, O flags based on op1 - op2
- **CALL** (0x2F): 1 operand - Call subroutine
  - Operands: target
  - Side Effects: Pushes return address to stack, PC = target
- **INT** (0x30): 1 operand - Software interrupt
  - Operands: vector
  - Side Effects: Pushes PC and flags, jumps to interrupt vector

## Advanced Control Flow
- **CALLZ** (0x9D): 1 operand - Call if zero
  - Operands: target
  - Side Effects: Calls if Z set
- **CALLNZ** (0x9E): 1 operand - Call if not zero
  - Operands: target
  - Side Effects: Calls if Z clear
- **RETN** (0x9F): 1 operand - Return with value
  - Operands: value
  - Side Effects: Pops return address, sets register to value
- **LOOPZ** (0xA0): 2 operands - Loop while zero
  - Operands: counter, target
  - Side Effects: Decrements counter, jumps if counter != 0 and Z set
- **WHILE** (0xA1): 1 operand - While loop start
  - Operands: condition
  - Side Effects: Evaluates condition for loop
- **LOOP** (0x5A): 2 operands - Loop instruction
  - Operands: counter, target
  - Side Effects: Decrements counter, jumps if counter != 0

## Graphics Operations
- **SBLEND** (0x31): 1 operand - Set blend mode
  - Operands: mode (0-4)
  - Side Effects: Sets graphics blend mode
- **SREAD** (0x32): 1 operand - Read screen pixel
  - Operands: dest
  - Side Effects: Reads pixel at VX,VY to dest
- **SWRITE** (0x33): 1 operand - Write screen pixel
  - Operands: color
  - Side Effects: Writes color to VX,VY
- **SROL** (0x34): 2 operands - Roll screen by axis, amount
  - Operands: axis, amount
  - Side Effects: Rolls screen
- **SROT** (0x35): 2 operands - Rotate screen by direction, amount
  - Operands: direction, amount
  - Side Effects: Rotates screen
- **SSHFT** (0x36): 2 operands - Shift screen by axis, amount
  - Operands: axis, amount
  - Side Effects: Shifts screen
- **SFLIP** (0x37): 2 operands - Flip screen by axis, amount
  - Operands: axis, amount
  - Side Effects: Flips screen
- **SLINE** (0x38): 2 operands - Line end x, end y
  - Operands: end_x, end_y
  - Side Effects: Draws line from VX,VY to end_x,end_y
- **SRECT** (0x39): 3 operands - Rectangle end x, end y, filled
  - Operands: end_x, end_y, filled
  - Side Effects: Draws rectangle
- **SCIRC** (0x3A): 2 operands - Circle radius, filled
  - Operands: radius, filled
  - Side Effects: Draws circle at VX,VY
- **SINV** (0x3B): 0 operands - Invert screen colors
  - Operands: None
  - Side Effects: Inverts all screen pixels
- **SBLIT** (0x3C): 0 operands - Blit screen
  - Side Effects: Blits screen buffer
- **SFILL** (0x3D): 1 operand - Fill screen
  - Operands: color
  - Side Effects: Fills screen with color

## VRAM Operations
- **VREAD** (0x3E): 1 operand - Read VRAM
  - Operands: dest
  - Side Effects: Reads VRAM at VX,VY to dest
- **VWRITE** (0x3F): 1 operands - Write VRAM
  - Operands: value
  - Side Effects: Writes to VRAM at VX,VY
- **VBLIT** (0x40): 0 operands - Blit VRAM
  - Side Effects: Blits VRAM buffer

## Text Operations
- **CHAR** (0x41): 1 operand - Draw character
  - Operands: char_code
  - Side Effects: Uses the low 8 bits of `char_code`, draws the glyph at VX,VY, advances VX by 8 pixels
- **TEXT** (0x42): 1 operand - Draw text
  - Operands: str_addr
  - Side Effects: Reads a null-terminated byte string from memory, interprets `0x09` as tab, `0x0A` as newline, `0x0D` as carriage return, draws all other bytes as glyph codes, updates VX/VY to the final cursor position

## Keyboard Operations
- **KEYIN** (0x43): 1 operand - Read key
  - Operands: dest
  - Side Effects: Reads key to dest, removes from buffer
- **KEYSTAT** (0x44): 1 operand - Check key status
  - Operands: dest
  - Side Effects: Sets dest to 1 if key available
- **KEYCOUNT** (0x45): 1 operand - Get key count
  - Operands: dest
  - Side Effects: Sets dest to buffer count
- **KEYCLEAR** (0x46): 1 operand - Clear keyboard buffer
  - Operands: None (operand ignored?)
  - Side Effects: Clears buffer
- **KEYCTRL** (0x47): 1 operand - Keyboard control
  - Operands: control
  - Side Effects: Sets keyboard control flags

## Random Operations
- **RND** (0x48): 1 operand - Random number
  - Operands: dest
  - Side Effects: Sets dest to random 0-255
- **RNDR** (0x49): 3 operands - Random number in range
  - Operands: dest, min, max
  - Side Effects: Sets dest to random in [min, max]

## Memory Operations
- **MEMCPY** (0x4A): 3 operands - Memory copy
  - Operands: dest, src, length
  - Side Effects: Copies length bytes from src to dest
- **MEMSET** (0x7C): 3 operands - Memory set
  - Operands: addr, value, length
  - Side Effects: Sets length bytes to value
- **MEMTEST** (0x7D): 3 operands - Memory test
  - Operands: addr1, addr2, length
  - Side Effects: Compares, sets flags
- **MEMMOVE** (0x7E): 3 operands - Memory move
  - Operands: dest, src, length
  - Side Effects: Moves length bytes
- **MEMCMP** (0x99): 4 operands - Memory compare
  - Operands: dest, addr1, addr2, length
  - Side Effects: Compares, stores result in dest
- **MEMSWAP** (0x9A): 3 operands - Memory swap
  - Operands: addr1, addr2, length
  - Side Effects: Swaps length bytes

## String Operations
- **STRCPY** (0x71): 2 operands - String copy
  - Operands: dest_addr, src_addr
  - Side Effects: Copies null-terminated string
- **STRCAT** (0x72): 2 operands - String concatenate
  - Operands: dest_addr, src_addr
  - Side Effects: Appends src to dest
- **STRCMP** (0x73): 3 operands - String compare
  - Operands: str1_addr, str2_addr, length
  - Side Effects: Compares up to length, sets flags
- **STRLEN** (0x74): 1 operand - String length
  - Operands: str_addr
  - Side Effects: Stores length in R0, sets flags
- **STREXT** (0x75): 4 operands - String extract
  - Operands: dest_addr, haystack_addr, needle_addr, max_len
  - Side Effects: Extracts substring, sets Z flag
- **STREXTI** (0x76): 4 operands - String extract case-insensitive
  - Operands: dest_addr, haystack_addr, needle_addr, max_len
  - Side Effects: Extracts substring (case-insens), sets Z flag
- **STRUPR** (0x77): 1 operand - String to uppercase
  - Operands: str_addr
  - Side Effects: Converts string in-place
- **STRLWR** (0x78): 1 operand - String to lowercase
  - Operands: str_addr
  - Side Effects: Converts string in-place
- **STRREV** (0x79): 1 operand - String reverse
  - Operands: str_addr
  - Side Effects: Reverses string in-place
- **STRFIND** (0x7A): 2 operands - String substring exists
  - Operands: haystack_addr, needle_addr
  - Side Effects: Sets Z flag if found
- **STRFINDI** (0x7B): 2 operands - String case-insensitive substring exists
  - Operands: haystack_addr, needle_addr
  - Side Effects: Sets Z flag if found (case-insens)

## Type Conversion
- **ITOB** (0x83): 2 operands - Integer to binary
  - Operands: value, dest_addr
  - Side Effects: Converts int to binary string
- **BTOI** (0x84): 2 operands - Binary to integer
  - Operands: str_addr, dest
  - Side Effects: Converts binary string to int
- **ITOS** (0x85): 2 operands - Integer to string
  - Operands: value, dest_addr
  - Side Effects: Converts int to decimal string
- **STOI** (0x86): 2 operands - String to integer
  - Operands: str_addr, dest
  - Side Effects: Converts string to int

## BCD Operations
- **SED** (0x4B): 1 operand - Set decimal flag
  - Operands: None (operand ignored?)
  - Side Effects: Sets decimal mode
- **CLD** (0x4C): 1 operand - Clear decimal flag
  - Operands: None
  - Side Effects: Clears decimal mode
- **CLA** (0x4D): 1 operand - Clear auxiliary carry
  - Operands: None
  - Side Effects: Clears auxiliary carry
- **BCDA** (0x4E): 1 operand - BCD add with carry
  - Operands: value
  - Side Effects: BCD add, sets flags
- **BCDS** (0x4F): 1 operand - BCD subtract with carry
  - Operands: value
  - Side Effects: BCD subtract, sets flags
- **BCDCMP** (0x50): 1 operand - BCD compare
  - Operands: value
  - Side Effects: BCD compare, sets flags
- **BCD2BIN** (0x51): 1 operand - BCD to binary
  - Operands: value
  - Side Effects: Converts BCD to binary
- **BIN2BCD** (0x52): 1 operand - Binary to BCD
  - Operands: value
  - Side Effects: Converts binary to BCD
- **BCDADD** (0x53): 1 operand - BCD add immediate
  - Operands: value
  - Side Effects: BCD add immediate
- **BCDSUB** (0x54): 1 operand - BCD subtract immediate
  - Operands: value
  - Side Effects: BCD subtract immediate

## Math Functions
- **POWR** (0x5B): 2 operands - Power base, exponent
  - Operands: base, exponent
  - Side Effects: Computes base^exponent, sets flags
- **SQRT** (0x5C): 1 operand - Square root
  - Operands: value
  - Side Effects: Computes sqrt, sets flags
- **LOG** (0x5D): 1 operand - Logarithm
  - Operands: value
  - Side Effects: Computes log, sets flags
- **EXP** (0x5E): 1 operand - Exponential
  - Operands: value
  - Side Effects: Computes exp, sets flags
- **SIN** (0x5F): 1 operand - Sine
  - Operands: value
  - Side Effects: Computes sin, sets flags
- **COS** (0x60): 1 operand - Cosine
  - Operands: value
  - Side Effects: Computes cos, sets flags
- **TAN** (0x61): 1 operand - Tangent
  - Operands: value
  - Side Effects: Computes tan, sets flags
- **ATAN** (0x62): 1 operand - Arctangent
  - Operands: value
  - Side Effects: Computes atan, sets flags
- **ASIN** (0x63): 1 operand - Arcsine
  - Operands: value
  - Side Effects: Computes asin, sets flags
- **ACOS** (0x64): 1 operand - Arccosine
  - Operands: value
  - Side Effects: Computes acos, sets flags
- **DEG** (0x65): 1 operand - Degrees to radians
  - Operands: value
  - Side Effects: Converts deg to rad
- **RAD** (0x66): 1 operand - Radians to degrees
  - Operands: value
  - Side Effects: Converts rad to deg
- **FLOOR** (0x67): 1 operand - Floor value
  - Operands: value
  - Side Effects: Computes floor
- **CEIL** (0x68): 1 operand - Ceiling value
  - Operands: value
  - Side Effects: Computes ceil
- **ROUND** (0x69): 1 operand - Round value
  - Operands: value
  - Side Effects: Computes round
- **TRUNC** (0x6A): 1 operand - Truncate value
  - Operands: value
  - Side Effects: Computes trunc
- **FRAC** (0x6B): 1 operand - Fractional part
  - Operands: value
  - Side Effects: Computes fractional part
- **INTGR** (0x6C): 1 operand - Integer part
  - Operands: value
  - Side Effects: Computes integer part

## Sprite Operations
- **SPBLIT** (0x55): 1 operand - Blit sprite
  - Operands: sprite_id
  - Side Effects: Blits sprite to screen
- **SPBLITALL** (0x56): 0 operands - Blit all sprites
  - Side Effects: Blits all sprites

## Sound Operations
- **SPLAY** (0x57): 0 operands - Play sound
  - Operands: None
  - Side Effects: Starts sound playback
- **SSTOP** (0x58): 0 operands - Stop sound
  - Operands: None
  - Side Effects: Stops sound playback
- **STRIG** (0x59): 1 operand - Trigger sound effect
  - Operands: effect_id
  - Side Effects: Triggers sound effect
- **SMIX** (0x7F): 1 operand - Mix channels
  - Operands: output
  - Side Effects: Mixes sound channels
- **SECHO** (0x80): 2 operands - Echo channel, delay
  - Operands: channel, delay
  - Side Effects: Applies echo
- **SREVERB** (0x81): 2 operands - Reverb channel, amount
  - Operands: channel, amount
  - Side Effects: Applies reverb
- **SFILTER** (0x82): 2 operands - Filter channel, type
  - Operands: channel, type
  - Side Effects: Applies filter

## Special Registers
These are special register access instructions, operands are values to set/get.

- **C0** (0xC3): 1 operand - RTC seconds low word (epoch 2018-07-17 UTC)
- **C1** (0xC4): 1 operand - RTC seconds high word (epoch 2018-07-17 UTC)
- **MX** (0xC5): 1 operand - Mouse X position
- **MY** (0xC6): 1 operand - Mouse Y position
- **MB** (0xC7): 1 operand - Mouse buttons
- **VC** (0xC8): 1 operand - Video Color
- **P0:** (0xC9): 1 operand - P0 high byte
- **P1:** (0xCA): 1 operand - P1 high byte
- **P2:** (0xCB): 1 operand - P2 high byte
- **P3:** (0xCC): 1 operand - P3 high byte
- **P4:** (0xCD): 1 operand - P4 high byte
- **P5:** (0xCE): 1 operand - P5 high byte
- **P6:** (0xCF): 1 operand - P6 high byte
- **P7:** (0xD0): 1 operand - P7 high byte
- **P8:** (0xD1): 1 operand - P8 high byte
- **P9:** (0xD2): 1 operand - P9 high byte
- **:P0** (0xD3): 1 operand - P0 low byte
- **:P1** (0xD4): 1 operand - P1 low byte
- **:P2** (0xD5): 1 operand - P2 low byte
- **:P3** (0xD6): 1 operand - P3 low byte
- **:P4** (0xD7): 1 operand - P4 low byte
- **:P5** (0xD8): 1 operand - P5 low byte
- **:P6** (0xD9): 1 operand - P6 low byte
- **:P7** (0xDA): 1 operand - P7 low byte
- **:P8** (0xDB): 1 operand - P8 low byte
- **:P9** (0xDC): 1 operand - P9 low byte
- **SA** (0xDD): 1 operand - Sound Address
- **SF** (0xDE): 1 operand - Sound Frequency
- **SV** (0xDF): 1 operand - Sound Volume
- **SW** (0xE0): 1 operand - Sound Waveform
- **VM** (0xE1): 1 operand - Video Mode
- **VL** (0xE2): 1 operand - Video Layer
- **TT** (0xE3): 1 operand - Timer
- **TM** (0xE4): 1 operand - Timer Match
- **TC** (0xE5): 1 operand - Timer Control
- **TS** (0xE6): 1 operand - Timer Speed
- **R0** (0xE7): 1 operand - Register R0
- **R1** (0xE8): 1 operand - Register R1
- **R2** (0xE9): 1 operand - Register R2
- **R3** (0xEA): 1 operand - Register R3
- **R4** (0xEB): 1 operand - Register R4
- **R5** (0xEC): 1 operand - Register R5
- **R6** (0xED): 1 operand - Register R6
- **R7** (0xEE): 1 operand - Register R7
- **R8** (0xEF): 1 operand - Register R8
- **R9** (0xF0): 1 operand - Register R9
- **P0** (0xF1): 1 operand - Register P0
- **P1** (0xF2): 1 operand - Register P1
- **P2** (0xF3): 1 operand - Register P2
- **P3** (0xF4): 1 operand - Register P3
- **P4** (0xF5): 1 operand - Register P4
- **P5** (0xF6): 1 operand - Register P5
- **P6** (0xF7): 1 operand - Register P6
- **P7** (0xF8): 1 operand - Register P7
- **P8** (0xF9): 1 operand - Register P8
- **P9** (0xFA): 1 operand - Register P9
- **SP** (0xFB): 1 operand - Stack Pointer
- **FP** (0xFC): 1 operand - Frame Pointer
- **VX** (0xFD): 1 operand - Video X coordinate
- **VY** (0xFE): 1 operand - Video Y coordinate
- **BANK** (0xC2): 1 operand - Bank select (0-15) for the 0x8000-0xBFFF windowed memory expansion. Bank 0 (default) is the base memory itself; banks 1-15 are separate 16KB pages.

## Notes
- Decimal immediates are undecorated, hex is prefixed with '0x'.
- Flags: Z (zero), C (carry), S (sign), O (overflow), I (interrupt), T (trap), B (break), D (decimal), P (parity), H (unused), A (auxiliary), E (error).
- For string operations, addresses point to null-terminated strings.
- Graphics operations often use VX, VY for coordinates and VC for color.

# Assembler Directives
- **DB, DW, DS** Define byte, word, or space
- **DEFSTR** Define a string, automatically null-terminates.
- **MACRO/ENDM** Define a macro
- **ORG** Set where code goes in memory. NOTE: The first ORG directive is what PC sets to on binary loading.
- **Label:** Labels for code sections
- **EQU** Define constants