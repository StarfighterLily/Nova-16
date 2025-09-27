MOV VM, 0
MOV VL, 0
; ClrDraw - simplified
L1:
KEYSTAT R0
CMP R0, 0
JZ L1
HLT