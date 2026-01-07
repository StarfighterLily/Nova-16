; NoBASIC compiler output
; Generated for Nova-16
ORG 0x0200
MOV P7:, 0xFF
MOV :P7, 0xFF
MOV SP, P7
MOV FP, SP
MOV R0, 5
MOV P1, R0
PUSH P1
; Free R0 (last use)
MOV R0, 3
MOV P1, R0
PUSH P1
; Free R0 (last use)
CALL _func_add_0
ADD SP, 4
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
TEXT STR5
ADD VY, 8
MOV R0, 7
MOV P1, R0
PUSH P1
; Free R0 (last use)
CALL _func_double_1
ADD SP, 2
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
TEXT STR5
ADD VY, 8
MOV R0, 10
MOV P1, R0
PUSH P1
; Free R0 (last use)
MOV R0, 15
MOV P1, R0
PUSH P1
; Free R0 (last use)
CALL _func_addwithtemp_2
ADD SP, 4
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
TEXT STR5
ADD VY, 8
MOV R0, 42
MOV P1, R0
PUSH P1
; Free R0 (last use)
CALL _func_greet_3
ADD SP, 2
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
TEXT STR5
ADD VY, 8
MOV R0, 99
MOV P1, R0
PUSH P1
; Free R0 (last use)
CALL _func_greet_3
ADD SP, 2
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
TEXT STR5
ADD VY, 8
MOV R0, 10
MOV P1, R0
PUSH P1
; Free R0 (last use)
MOV R0, 20
MOV P1, R0
PUSH P1
; Free R0 (last use)
CALL _func_makepoint_4
ADD SP, 4
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
TEXT STR5
ADD VY, 8
MOV R0, 5
MOV P1, R0
PUSH P1
; Free R0 (last use)
MOV R0, 20
MOV P1, R0
PUSH P1
; Free R0 (last use)
CALL _func_makepoint_4
ADD SP, 4
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
MOV VX, 0
MOV VC, 15
TEXT STR5
ADD VY, 8
MOV R0, 5
MOV P1, R0
PUSH P1
; Free R0 (last use)
MOV R0, 10
MOV P1, R0
PUSH P1
; Free R0 (last use)
CALL _func_makepoint_4
ADD SP, 4
MOV R1, R0
MOV P2, R1
MOV VX, 0
MOV VC, 15
TEXT STR12
ADD VY, 8
MOV R0, P2
ITOS P1, R0
MOV VX, 0
MOV VC, 15
TEXT P1
ADD VY, 8
MOV VX, 0
MOV VC, 15
TEXT STR5
ADD VY, 8
MOV R0, 5
MOV P1, R0
PUSH P1
; Free R0 (last use)
CALL _func_factorial_5
ADD SP, 2
MOV R1, R0
MOV P2, R1
MOV VX, 0
MOV VC, 15
TEXT STR13
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
ADD P0, 4
MOV P1, [P0]
; Preserve left operand in register across right-side evaluation
MOV R2, P1
MOV P0, FP
ADD P0, 6
MOV R4, [P0]
MOV R0, R2
ADD R0, R4
; Free R4 (last use)
LEAVE
RET

_func_double_1:
; Function: double
; Parameters: x
; Locals:  (0 bytes)
ENTER 0
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
; Preserve left operand in register across right-side evaluation
MOV R2, P1
MOV R3, 1
SHL R3, 1
MOV R1, R2
MUL R1, R3
; Free R3 (last use)
MOV P0, FP
ADD P0, 4
MOV [P0], R1
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
MOV R0, P1
; Free P1 (last use)
LEAVE
RET

_func_addwithtemp_2:
; Function: addwithtemp
; Parameters: a, b
; Locals: temp (2 bytes)
ENTER 2
; LOCAL variable: temp @ FP-2
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
; Preserve left operand in register across right-side evaluation
MOV R2, P1
MOV P0, FP
ADD P0, 6
MOV R4, [P0]
MOV R1, R2
ADD R1, R4
; Free R4 (last use)
MOV P0, FP
ADD P0, -2
MOV [P0], R1
MOV P0, FP
ADD P0, -2
MOV P1, [P0]
MOV R0, P1
; Free P1 (last use)
LEAVE
RET

_func_greet_3:
; Function: greet
; Parameters: name
; Locals:  (0 bytes)
ENTER 0
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
MOV R0, P1
; Free P1 (last use)
LEAVE
RET

_func_makepoint_4:
; Function: makepoint
; Parameters: x, y
; Locals:  (0 bytes)
ENTER 0
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
; Preserve left operand in register across right-side evaluation
MOV R2, P1
MOV P0, FP
ADD P0, 6
MOV R4, [P0]
MOV R0, R2
ADD R0, R4
; Free R4 (last use)
LEAVE
RET

_func_factorial_5:
; Function: factorial
; Parameters: n
; Locals:  (0 bytes)
ENTER 0
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
MOV R3, 1
CMP P1, R3
; Free P1 (last use)
; Free R3 (last use)
MOV R1, 0
JLE L3
JMP L4
L3:
MOV R1, 1
L4:
CMP R1, 0
JZ L1
MOV R0, 1
LEAVE
RET
L1:
MOV P0, FP
ADD P0, 4
MOV P1, [P0]
; Preserve left operand in register across right-side evaluation
MOV R2, P1
MOV P0, FP
ADD P0, 4
MOV R6, [P0]
; Preserve left operand in register across right-side evaluation
MOV R7, R6
MOV R8, 1
MOV R4, R7
SUB R4, R8
; Free R8 (last use)
MOV P2, R4
PUSH P2
; Free R4 (last use)
CALL _func_factorial_5
ADD SP, 2
MOV R3, R0
MOV R0, R2
MUL R0, R3
; Free R3 (last use)
LEAVE
RET
STR4: DEFSTR "Add(5,3) = "
STR5: DEFSTR ""
STR6: DEFSTR "Double(7) = "
STR7: DEFSTR "AddWithTemp(10,15) = "
STR8: DEFSTR "Greet() = "
STR9: DEFSTR "Greet(99) = "
STR10: DEFSTR "MakePoint() = "
STR11: DEFSTR "MakePoint(5) = "
STR12: DEFSTR "MakePoint(5,10) = "
STR13: DEFSTR "Factorial(5) = "