; linklib.asm -- library module providing ADDAB
GLOBAL ADDAB
ADDAB: ADD R0, R1
       MOV P2, R0
       HLT
