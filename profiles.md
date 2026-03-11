# Asm profiles
`gfxtest.bin` 500k cycles
Top 10 instructions by frequency:
  MOV: 131088 (26.2%)
  INC: 131071 (26.2%)
  SWRITE: 65536 (13.1%)
  CMP: 65535 (13.1%)
  JNZ: 65535 (13.1%)
  JMP: 41115 (8.2%)
  SROL: 59 (0.0%)
  IRET: 59 (0.0%)
  STI: 1 (0.0%)
  TEXT: 1 (0.0%)

`pixelfill.bin` 458754 cycles
  Top 10 instructions by frequency:
  MOV: 131076 (28.6%)
  SWRITE: 65536 (14.3%)
  INC: 65535 (14.3%)
  CMP: 65535 (14.3%)
  JZ: 65535 (14.3%)
  JMP: 65534 (14.3%)
  XOR: 2 (0.0%)
  HLT: 1 (0.0%)

`starfield.bin` 500k cycles
Top 10 instructions by frequency:
  JMP: 486969 (97.4%)
  MOV: 4388 (0.9%)
  RND: 1408 (0.3%)
  SWRITE: 1408 (0.3%)
  ADD: 1408 (0.3%)
  RNDR: 1408 (0.3%)
  CMP: 1408 (0.3%)
  JGE: 1408 (0.3%)
  SROL: 144 (0.0%)
  IRET: 48 (0.0%)

# NoBASIC profiles
`starfield.bin` 500k cycles
Top 10 instructions by frequency:
  CMP: 121932 (24.4%)
  JGT: 121932 (24.4%)
  JMP: 119077 (23.8%)
  INC: 119009 (23.8%)
  MOV: 12449 (2.5%)
  XOR: 3131 (0.6%)
  RND: 660 (0.1%)
  SUB: 394 (0.1%)
  RNDR: 330 (0.1%)
  SWRITE: 330 (0.1%)

`screen_fill.bin` 500k cycles
Top 10 instructions by frequency:
  MOV: 249679 (49.9%)
  CMP: 41856 (8.4%)
  JGT: 41856 (8.4%)
  INC: 41692 (8.3%)
  JMP: 41692 (8.3%)
  SWRITE: 41530 (8.3%)
  ADD: 41530 (8.3%)
  XOR: 165 (0.0%)