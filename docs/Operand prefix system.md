Addressing Modes in Nova-16
The Nova-16 uses a prefixed operand architecture where each instruction consists of:

Opcode (1 byte) - core operation
Mode byte (1 byte) - operand addressing modes
Operand data - variable length based on modes
Memory Addressing Modes (Mode = 3)
When an operand uses mode 3, it supports four memory addressing sub-modes:

Direct Memory Addressing: [0xADDR]

Example: MOV R0, [0x2000]
Encodes a 16-bit address directly
Register Indirect: [REG]

Example: MOV R0, [P2]
Address stored in P or R register
Register Indexed: [REG + offset]

Example: MOV R0, [P2 + 8]
Base address in register + immediate offset
Direct Indexed: [0xADDR + offset]

Example: MOV R0, [0x2000 + 4]
Direct address + immediate offset
Instructions That Support Memory Operands
All instructions that take operands can use memory references, since they all use the same operand parsing system. Here are the categories:

Data Movement Instructions
MOV - Move data between operands (supports all addressing modes)
XCHNG - Exchange values (supports memory operands)
LEA - Load effective address (computes memory addresses)
SWAP - Swap nibbles (can operate on memory)
Arithmetic Instructions
ADD, SUB, MUL, DIV, MOD - All support memory operands
INC, DEC - Increment/decrement memory locations
NEG, ABS - Unary operations on memory
ADC, SBC - Add/subtract with carry (memory operands)
Bitwise Instructions
AND, OR, XOR, NOT - All support memory operands
SHL, SHR, ROL, ROR - Shift/rotate operations on memory
SAL, SAR, RCL, RCR - Advanced shift/rotate operations
Comparison Instructions
CMP - Compare operands (supports memory operands)
BTST, BSET, BCLR, BFLIP - Bit test and modify operations
Control Flow Instructions
JMP, JNZ, JZ, etc. - Jump instructions (target can be memory address)
CALL, CALLI - Call instructions (target can be memory address)
JMPI - Jump indirect (loads address from memory)
Stack Instructions
PUSH, POP - Push/pop values to/from memory (stack)
Memory-Specific Instructions
MEMCPY - Memory copy (takes source/dest addresses as operands)
MEMSET - Memory set (takes address as operand)
MEMTEST - Memory test/compare (takes addresses as operands)
MEMMOVE - Memory move (takes addresses as operands)
MEMCMP - Memory compare (takes addresses as operands)
MEMSWAP - Memory swap (takes addresses as operands)
Graphics Instructions
SREAD - Read screen pixel (address computed from coordinates)
SWRITE - Write screen pixel (address computed from coordinates)
VREAD, VWRITE - VRAM operations (take addresses)
VBLIT - VRAM blit (takes address)
String Instructions
STRCPY, STRCAT, STRCMP - String operations (take memory addresses)
STRLEN, STRREV - String operations on memory
STREXT, STREXTI - String extract operations
STRUPR, STRLWR - String case conversion
STRFIND, STRFINDI - String search operations
I/O Instructions
KEYIN, KEYSTAT - Keyboard operations (access memory buffers)
TEXT, CHAR - Text output (access memory strings)
Math Instructions
POWR, SQRT, LOG, EXP - Math operations (can use memory operands)
SIN, COS, TAN, etc. - Trigonometric functions
FLOOR, CEIL, ROUND, TRUNC - Rounding operations
MIN, MAX - Min/max operations
Conversion Instructions
ITOB, BTOI - Integer/binary conversion
ITOS, STOI - Integer/string conversion
Instructions That Operate Directly on Memory
Beyond just accepting memory addresses as operands, some instructions are specifically designed to operate directly on memory regions:

Bulk Memory Operations
MEMCPY - Copies data between memory regions
MEMSET - Fills memory regions with a value
MEMTEST - Compares memory regions
MEMMOVE - Moves data (handles overlapping regions)
MEMCMP - Compares memory regions byte-by-byte
MEMSWAP - Swaps memory regions
Memory Increment/Decrement
INCM - Increment memory location
DECM - Decrement memory location
Graphics Memory Operations
SFILL - Fill screen memory
SBLIT - Blit screen regions
VBLIT - Blit VRAM regions
SPBLIT, SPBLITALL - Sprite blitting operations
Key Points
Universal Memory Support: Any instruction with operands can use memory references - the architecture doesn't restrict memory operands to specific instructions.

Flexible Addressing: All four memory addressing modes (direct, indirect, indexed, direct-indexed) work with any instruction that supports memory operands.

Memory-Memory Operations: Instructions like MOV can perform memory-to-memory transfers directly.

Address Calculation: Instructions like LEA can compute effective addresses for complex memory operations.

Bulk Operations: Dedicated memory instructions handle large data transfers and comparisons efficiently.

The Nova-16's design provides comprehensive memory access capabilities across nearly all instructions, making it highly flexible for memory-intensive operations.