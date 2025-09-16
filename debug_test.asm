
ORG 0x1000
SETUP:
    STI               
    MOV TT, 0         
    MOV TM, 5         
    MOV TS, 0         
    MOV TC, 3         

LOOP:
    NOP               
    JMP LOOP          

ORG 0x0100            
    INC R1            
    HLT               ; Halt instead of IRET to see if we get here
    