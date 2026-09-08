; main.nobj -- consumer module
EXTERN ADDAB
GLOBAL START
START: MOV R0, 10
       MOV R1, 32
       MOV P0, ADDAB
       JNZ P0
       HLT
