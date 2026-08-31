; WARNING: 2 variable(s) using dedicated spill slots
;          Spilled variables: temp1, gameLevel
;          Spill region: 0x7000-0x7004
;          Register pressure: 5 (max), 5 available
;          This will impact performance. Consider:
;          - Reducing total variable count (currently 14)
;          - Reducing variable lifetimes by localizing scope
;          - Breaking complex expressions into simpler parts
; NoBASIC compiler output
; Generated for Nova-16
ORG 0x0200
MOV P7:, 0xFF
MOV R1, 100
MOV :P7, 0xFF
MOV P2, R1
MOV SP, P7
MOV R1, 200
MOV FP, SP
MOV P2, R1
MOV P2, 42
; GLOBAL variable: playerScore @ 0x0120
; GLOBAL variable: playerLives @ 0x0122
; GLOBAL variable: gameLevel @ 0x0124
; GLOBAL variable: highScore @ 0x0126
XOR R1, R1
MOV P2, R1
MOV P1, 128
MOV R1, 3
MOV P0, 0
MOV P3, R1
MOV :P0, 1
MOV [P1], P0
MOV P4, 9999
; GLOBAL variable: temp1 @ 0x0128
; GLOBAL variable: temp2 @ 0x012A
; GLOBAL variable: temp3 @ 0x012C
; GLOBAL variable: temp4 @ 0x012E
MOV R1, 10
MOV P1, 130
MOV P0, 0
MOV :P0, R1
MOV [P1], P0
MOV P5, 20
MOV P6, 30
MOV P4, 40
MOV P3, 100
MOV P4, 1
MOV R0, 5
L1:
CMP P4, R0
JGT L2
MOV P0, 128
MOV P0, [P0]
; Preserve left operand in register across right-side evaluation
MUL R0, P4
MOV R3, P0
MOV R0, R3
; Preserve left operand in register across right-side evaluation
MOV R1, R0
ADD R1, P2
INC P4
MOV P2, R1
JMP L1
L2:
MOV R1, 50
MOV R0, 50
MOV P3, R1
; Preserve left operand in register across right-side evaluation
MOV R1, R0
ADD R1, P2
MOV P2, R1
; ClrDraw
MOV VL, 1
MOV VM, 0
SFILL 0x00
XOR VL, VL
MOV VX, 10
MOV VY, 10
MOV VC, 15
MOV VM, 0
TEXT STR2
MOV VC, 10
MOV VX, 10
MOV VY, 30
TEXT STR3
MOV VC, 10
MOV VX, 10
MOV VY, 40
TEXT STR4
MOV VC, 10
MOV VX, 10
MOV VY, 50
TEXT STR5
MOV VC, 14
MOV VX, 10
MOV VY, 70
TEXT STR6
MOV VC, 14
MOV VX, 10
MOV VY, 80
TEXT STR7
MOV VC, 14
MOV VX, 10
MOV VY, 90
TEXT STR8
MOV VC, 12
MOV VX, 10
MOV VY, 110
TEXT STR9
MOV VC, 12
MOV VX, 10
MOV VY, 120
TEXT STR10
MOV VY, 140
MOV VC, 1
SHL VC, 1
MOV VX, 10
TEXT STR11
L13:
KEYSTAT R0
CMP R0, 0
JZ L13
HLT
STR2: DEFSTR "Variable Scoping Test"
STR3: DEFSTR "x ="
STR4: DEFSTR "y ="
STR5: DEFSTR "implicitVar ="
STR6: DEFSTR "playerScore ="
STR7: DEFSTR "playerLives ="
STR8: DEFSTR "gameLevel ="
STR9: DEFSTR "totalTemp ="
STR10: DEFSTR "bonus ="
STR11: DEFSTR "All tests passed!"