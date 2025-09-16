; Very simple stack test
ORG 0x1000

MOV P0, 0x1234
PUSH P0
POP P1
HLT
