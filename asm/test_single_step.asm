; Test single-step trap mode
; This program tests enabling and disabling single-step trap

ORG 0x0000

; Enable single-step trap
ENATRAP

; These instructions should trigger debug interrupts if interrupts enabled
MOV R0, 0x11
MOV R1, 0x22
MOV R2, 0x33

; Disable trap
DISATRAP

; These should not trigger
MOV R3, 0x44
MOV R4, 0x55

; End
HLT