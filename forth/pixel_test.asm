; Simple pixel test
ORG 0x1000

; Initialize stacks
MOV P8, 0xF000    ; Parameter stack pointer
MOV P9, 0xFFFF    ; Return stack pointer

main:
    ; Set video mode to coordinate mode
    MOV VM, 0
    
    ; Set active layer to 0
    MOV VL, 0
    
    ; Set coordinates
    MOV VX, 10
    MOV VY, 10
    
    ; Write pixel
    MOV R0, 255
    SWRITE R0
    
    HLT
