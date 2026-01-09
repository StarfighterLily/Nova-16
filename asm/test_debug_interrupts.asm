; Test hardware debugging with interrupt handling
; Sets up interrupt vector 7 for debug interrupts

ORG 0x0000

; Set up interrupt vector 7 (debug) at 0x0200
MOV P0, 0x0200
MOV [0x011C], P0    ; Write handler address to vector

; Enable interrupts
STI

; Set breakpoint at 0x0030
MOV R0, 0
MOV P1, 0x0030
SETBP R0, P1

; Enable breakpoints
ENABRK

; Execute some instructions
MOV R1, 0xAA

; At 0x0030 - breakpoint should trigger
MOV R2, 0xBB

; Continue after breakpoint
MOV R3, 0xCC

; Disable debugging
DISBRK
DISATRAP

; End
HLT

; Debug interrupt handler at 0x0200
ORG 0x0200
; Handler: just increment a counter and return
MOV R7, [0x0300]    ; Load counter
INC R7
MOV [0x0300], R7    ; Store counter
IRET