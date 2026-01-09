; Test hardware breakpoints
; This program tests setting, enabling, and clearing hardware breakpoints

ORG 0x0000

; Set breakpoint 0 at address 0x0020
MOV R0, 0          ; Index 0
MOV P1, 0x0020     ; Address 0x0020
SETBP R0, P1

; Set breakpoint 1 at address 0x0030
MOV R0, 1          ; Index 1
MOV P1, 0x0030     ; Address 0x0030
SETBP R0, P1

; Enable all breakpoints
ENABRK

; Some instructions to execute
MOV R1, 0xAA
MOV R2, 0xBB

; Clear breakpoint 0
MOV R0, 0
CLRBP R0

; Disable all breakpoints
DISBRK

; More instructions
MOV R3, 0xCC
MOV R4, 0xDD

; End
HLT