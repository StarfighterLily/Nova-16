; Comprehensive test for hardware debugging features
; Tests breakpoints and single-step trap together

ORG 0x0000

; Set up breakpoint at 0x0040
MOV R0, 0          ; Index 0
MOV P1, 0x0040     ; Address 0x0040
SETBP R0, P1

; Enable breakpoints
ENABRK

; Enable single-step trap
ENATRAP

; Execute some instructions
MOV R1, 0xAB
MOV R2, 0xCD

; At 0x0040 - this should trigger breakpoint if enabled
MOV R3, 0xEF

; Clear breakpoint
MOV R0, 0
CLRBP R0

; Disable breakpoints
DISBRK

; Disable trap
DISATRAP

; Final instructions
MOV R4, 0x12
MOV R5, 0x34

; End
HLT