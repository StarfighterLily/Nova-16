Instructions:
Prefix byte:
0x00: Memory Operations
0x01: Arithmetic/Logic  
0x02: BCD Operations
0x03: Timer Control
0x04: Graphics System
0x05: Sound System
0x06: Input/Keyboard
0x07: Control Flow
0x08: Stack Operations
0x09: Interrupt Control
0x0A: Debug/Profile
0x0B-0x0F: Reserved
Operation byte:
0x00-0xFF for each instruction per prefix byte, for instance:
```0x01 0x01```: (arithmetic)-ADD

Operands:
Operand prefix:
How to address the operand coming up
0x0X: Immediate value
0x1X: Direct access
0x2X: Indirect access
0x3X: Indexed access
0x4X: P:
0x5X: :P
0x6X: Rx:Rx+1
0x7X: Direct memory address

0xX0: 8 bit
0xX1: 16 bit
0xX2: register
0xX3: R:
0xX4: :R