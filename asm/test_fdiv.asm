; FDIV test
ORG 0x0000

MOV P0, 1920   ; 7.5
MOV P1, 768    ; 3.0
FDIV P0, P1    ; Should make P0 = 640 (2.5)
HLT