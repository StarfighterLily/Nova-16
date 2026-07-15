; NoBASIC compiler output
; Generated for Nova-16
ORG 0x0200
MOV P7:, 0xFF
MOV :P7, 0xFF
MOV SP, P7
MOV FP, SP
PUSH P2
MOV P1, 5
PUSH P1
; Free R0 (last use)
MOV P1, 3
PUSH P1
; Free R0 (last use)
CALL _func_add_0
ADD SP, 4
POP P2
MOV R1, R0
MOV P2, R1
MOV VX, 0
MOV VC, 15
TEXT STR2
ADD VY, 8
MOV R0, P2
ITOS P1, R0
MOV VX, 0
MOV VC, 15
TEXT P1
ADD VY, 8
MOV VX, 0
MOV VC, 15
TEXT STR3
ADD VY, 8
PUSH P2
MOV P1, 7
PUSH P1
; Free R0 (last use)
CALL _func_double_1
ADD SP, 2
POP P2
MOV R1, R0
MOV P2, R1
MOV VX, 0
MOV VC, 15
TEXT STR4
ADD VY, 8
MOV R0, P2
ITOS P1, R0
MOV VX, 0
MOV VC, 15
TEXT P1
ADD VY, 8
MOV VX, 0
MOV VC, 15
TEXT STR3
ADD VY, 8
PUSH P2
MOV P1, 10
PUSH P1
; Free R0 (last use)
MOV P1, 15
PUSH P1
; Free R0 (last use)
CALL _func_addwithtemp_2
ADD SP, 4
POP P2
MOV R1, R0
MOV P2, R1
MOV VX, 0
MOV VC, 15
TEXT STR5
ADD VY, 8
MOV R0, P2
ITOS P1, R0
MOV VX, 0
MOV VC, 15
TEXT P1
ADD VY, 8
MOV VX, 0
MOV VC, 15
TEXT STR3
ADD VY, 8
PUSH P2
MOV P1, 42
PUSH P1
; Free R0 (last use)
CALL _func_greet_3
ADD SP, 2
POP P2
MOV R1, R0
MOV P2, R1
MOV VX, 0
MOV VC, 15
TEXT STR6
ADD VY, 8
MOV R0, P2
ITOS P1, R0
MOV VX, 0
MOV VC, 15
TEXT P1
ADD VY, 8
MOV VX, 0
MOV VC, 15
TEXT STR3
ADD VY, 8
PUSH P2
MOV P1, 99
PUSH P1
; Free R0 (last use)
CALL _func_greet_3
ADD SP, 2
POP P2
MOV R1, R0
MOV P2, R1
MOV VX, 0
MOV VC, 15
TEXT STR7
ADD VY, 8
MOV R0, P2
ITOS P1, R0
MOV VX, 0
MOV VC, 15
TEXT P1
ADD VY, 8
MOV VX, 0
MOV VC, 15
TEXT STR3
ADD VY, 8
PUSH P2
MOV P1, 10
PUSH P1
; Free R0 (last use)
MOV P1, 20
PUSH P1
; Free R0 (last use)
CALL _func_makepoint_4
ADD SP, 4
POP P2
MOV R1, R0
MOV P2, R1
MOV VX, 0
MOV VC, 15
TEXT STR8
ADD VY, 8
MOV R0, P2
ITOS P1, R0
MOV VX, 0
MOV VC, 15
TEXT P1
ADD VY, 8
MOV VX, 0
MOV VC, 15
TEXT STR3
ADD VY, 8
PUSH P2
MOV P1, 5
PUSH P1
; Free R0 (last use)
MOV P1, 20
PUSH P1
; Free R0 (last use)
CALL _func_makepoint_4
ADD SP, 4
POP P2
MOV R1, R0
MOV P2, R1
MOV VX, 0
MOV VC, 15
TEXT STR9
ADD VY, 8
MOV R0, P2
ITOS P1, R0
MOV VX, 0
MOV VC, 15
TEXT P1
ADD VY, 8
MOV VX, 0
MOV VC, 15
TEXT STR3
ADD VY, 8
PUSH P2
MOV P1, 5
PUSH P1
; Free R0 (last use)
MOV P1, 10
PUSH P1
; Free R0 (last use)
CALL _func_makepoint_4
ADD SP, 4
POP P2
MOV R1, R0
MOV P2, R1
MOV VX, 0
MOV VC, 15
TEXT STR10
ADD VY, 8
MOV R0, P2
ITOS P1, R0
MOV VX, 0
MOV VC, 15
TEXT P1
ADD VY, 8
MOV VX, 0
MOV VC, 15
TEXT STR3
ADD VY, 8
PUSH P2
MOV P1, 5
PUSH P1
; Free R0 (last use)
CALL _func_factorial_5
ADD SP, 2
POP P2
MOV R1, R0
MOV P2, R1
MOV VX, 0
MOV VC, 15
TEXT STR11
ADD VY, 8
MOV R0, P2
ITOS P1, R0
MOV VX, 0
MOV VC, 15
TEXT P1
ADD VY, 8
HLT
_func_add_0:
; Function: add
; Parameters: a, b
; Locals:  (0 bytes)
ENTER 0
MOV P0, FP
ADD P0, 6
MOV P1, [P0]
; Preserve left operand in register across right-side evaluation
MOV R2, P1
MOV P0, FP
ADD P0, 4
MOV P2, [P0]
MOV R0, R2
ADD R0, P2
; Free P2 (last use)
MOV SP, FP
POP FP
RETN R0
_func_double_1:
; Function: double
; Parameters: x
; Locals:  (0 bytes)
ENTER 0
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
MOV R1, P1
SHL R1, 1
; Free P1 (last use)
MOV P0, FP
ADD P0, 4
MOV [P0], R1
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
MOV SP, FP
POP FP
RETN P1
_func_addwithtemp_2:
; Function: addwithtemp
; Parameters: a, b
; Locals: temp (2 bytes)
ENTER 2
; LOCAL variable: temp @ FP-2
MOV P0, FP
ADD P0, 6
MOV P1, [P0]
; Preserve left operand in register across right-side evaluation
MOV R2, P1
MOV P0, FP
ADD P0, 4
MOV P2, [P0]
MOV R1, R2
ADD R1, P2
; Free P2 (last use)
MOV P0, FP
ADD P0, -2
MOV [P0], R1
MOV P0, FP
ADD P0, -2
MOV P1, [P0]
MOV SP, FP
POP FP
RETN P1
_func_greet_3:
; Function: greet
; Parameters: name
; Locals:  (0 bytes)
ENTER 0
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
MOV SP, FP
POP FP
RETN P1
_func_makepoint_4:
; Function: makepoint
; Parameters: x, y
; Locals:  (0 bytes)
ENTER 0
MOV P0, FP
ADD P0, 6
MOV P1, [P0]
; Preserve left operand in register across right-side evaluation
MOV R2, P1
MOV P0, FP
ADD P0, 4
MOV P2, [P0]
MOV R0, R2
ADD R0, P2
; Free P2 (last use)
MOV SP, FP
POP FP
RETN R0
_func_factorial_5:
; Function: factorial
; Parameters: n
; Locals:  (0 bytes)
ENTER 0
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
MOV P2, 1
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JGT L1
MOV R0, 1
MOV SP, FP
POP FP
RETN R0
L1:
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
; Preserve left operand in register across right-side evaluation
MOV R2, P1
MOV P0, FP
ADD P0, 4
MOV P2, [P0]
; Preserve left operand in register across right-side evaluation
MOV R6, P2
MOV R7, 1
MOV R4, R6
SUB R4, R7
; Free R7 (last use)
MOV P3, R4
PUSH P3
; Free R4 (last use)
CALL _func_factorial_5
ADD SP, 2
MOV R3, R0
MOV R0, R2
MUL R0, R3
; Free R3 (last use)
MOV SP, FP
POP FP
RETN R0
STR2: DEFSTR "Add(5,3) = "
STR3: DEFSTR ""
STR4: DEFSTR "Double(7) = "
STR5: DEFSTR "AddWithTemp(10,15) = "
STR6: DEFSTR "Greet() = "
STR7: DEFSTR "Greet(99) = "
STR8: DEFSTR "MakePoint() = "
STR9: DEFSTR "MakePoint(5) = "
STR10: DEFSTR "MakePoint(5,10) = "
STR11: DEFSTR "Factorial(5) = "