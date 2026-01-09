; FTOI test
ORG 0x0000

MOV P0, 640    ; 2.5
FTOI P0        ; Should make P0 = 2
HLT