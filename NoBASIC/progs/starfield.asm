; NoBASIC compiler output
; Generated for Nova-16
ORG 0x0200
MOV P7:, 0xFF
MOV :P7, 0xFF
MOV SP, P7
MOV FP, SP
; Struct stext declared with fields: color, toggle
MOV R1, 1
SHL R1, 4
; Store to stext.color
MOV P1, R1
MOV P0, 288
MOV [P0], P1
XOR R1, R1
; Store to stext.toggle
MOV P1, R1
MOV P0, 290
MOV [P0], P1
XOR R1, R1
MOV P3, R1
MOV VM, 0
MOV R1, 40
MOV VL, 1
MOV R0, R1
L14:
CMP P3, R0
JGT L15
XOR R1, R1
MOV P2, R1
MOV P5, 40
L16:
CMP P2, P5
JGT L17
RND R1
MOV VX, R1
RND R1
MOV R2, 1
MOV R3, 1
SHL R3, 2
MOV VY, R1
RNDR R1, R2, R3
; Free R2 (last use)
; Free R3 (last use)
MOV VC, R1
SWRITE VC
INC P2
JMP L16
L17:
INC P3
JMP L14
L15:
MOV VL, 1
MOV VM, 0
SHL VL, 1
XOR R1, R1
MOV P3, R1
MOV R0, 20
L18:
CMP P3, R0
JGT L19
XOR R1, R1
MOV P2, R1
MOV P5, 20
L20:
CMP P2, P5
JGT L21
RND R1
MOV VX, R1
RND R1
MOV R3, 9
MOV VY, R1
MOV R2, 5
RNDR R1, R2, R3
; Free R2 (last use)
; Free R3 (last use)
MOV VC, R1
SWRITE VC
INC P2
JMP L20
L21:
INC P3
JMP L18
L19:
XOR R1, R1
MOV P3, R1
MOV VM, 0
MOV R1, 12
MOV VL, 3
MOV R0, R1
L22:
CMP P3, R0
JGT L23
XOR R1, R1
MOV P2, R1
MOV P5, 12
L24:
CMP P2, P5
JGT L25
RND R1
MOV VX, R1
RND R1
MOV R3, 15
MOV VY, R1
MOV R2, 10
RNDR R1, R2, R3
; Free R2 (last use)
; Free R3 (last use)
MOV VC, R1
SWRITE VC
INC P2
JMP L24
L25:
INC P3
JMP L22
L23:
L26:
MOV R1, 1
WHILE R1
JZ L27
PUSH P2
PUSH P3
CALL _func_scrollbg_0
POP P3
POP P2
PUSH P2
PUSH P3
CALL _func_flashtext_1
POP P3
POP P2
XOR R1, R1
MOV P3, R1
MOV R0, 25
L28:
CMP P3, R0
JGT L29
XOR R1, R1
MOV P2, R1
MOV P5, 25
L30:
CMP P2, P5
JGT L31
INC P2
JMP L30
L31:
INC P3
JMP L28
L29:
JMP L26
L27:
HLT
_func_scrollbg_0:
; Function: scrollbg
; Parameters:
; Locals:  (0 bytes)
ENTER 0
XOR R0, R0
MOV R1, 1
MOV VM, 0
MOV VL, 1
SROL R0, R1
; Free R0 (last use)
; Free R1 (last use)
MOV VL, 1
MOV R1, 1
SHL VL, 1
XOR R0, R0
SHL R1, 1
MOV VM, 0
SROL R0, R1
; Free R0 (last use)
; Free R1 (last use)
XOR R0, R0
MOV R1, 3
MOV VM, 0
MOV VL, 3
SROL R0, R1
; Free R0 (last use)
; Free R1 (last use)
MOV SP, FP
POP FP
RETN 0
_func_flashtext_1:
; Function: flashtext
; Parameters:
; Locals:  (0 bytes)
ENTER 0
MOV VL, 1
MOV VM, 0
SHL VL, 2
; Allocate struct stext (stext) at 0x0120
; Load stext.toggle
MOV P0, 290
MOV P1, [P0]
XOR P2, P2
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L1
; Load stext.color
MOV P0, 288
MOV P1, [P0]
; Preserve left operand in register across right-side evaluation
MOV R3, 1
MOV R2, P1
MOV R1, R2
ADD R1, R3
; Free R3 (last use)
; Store to stext.color
MOV P1, R1
MOV P0, 288
MOV [P0], P1
; Load stext.color
MOV P0, 288
MOV P1, [P0]
MOV P2, 31
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JLE L3
MOV R1, 31
; Store to stext.color
MOV P1, R1
MOV P0, 288
MOV [P0], P1
MOV R1, 1
; Store to stext.toggle
MOV P1, R1
MOV P0, 290
MOV [P0], P1
L3:
L1:
; Load stext.toggle
MOV P0, 290
MOV P1, [P0]
MOV P2, 1
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L5
; Load stext.color
MOV P0, 288
MOV P1, [P0]
; Preserve left operand in register across right-side evaluation
MOV R3, 1
MOV R2, P1
MOV R1, R2
SUB R1, R3
; Free R3 (last use)
; Store to stext.color
MOV P1, R1
MOV P0, 288
MOV [P0], P1
; Load stext.color
MOV P0, 288
MOV P1, [P0]
MOV P2, 1
SHL P2, 4
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JGE L7
MOV R1, 1
SHL R1, 4
; Store to stext.color
MOV P1, R1
MOV P0, 288
MOV [P0], P1
XOR R1, R1
; Store to stext.toggle
MOV P1, R1
MOV P0, 290
MOV [P0], P1
L7:
L5:
MOV VY, 120
MOV VX, 80
; Load stext.color
MOV P0, 288
MOV P1, [P0]
MOV VC, P1
TEXT STR8
XOR R0, R0
MOV P1, R0
MOV P2, 25
L10:
CMP P1, P2
JGT L11
XOR R0, R0
MOV P4, R0
MOV P5, 25
L12:
CMP P4, P5
JGT L13
INC P4
JMP L12
L13:
INC P1
JMP L10
L11:
MOV SP, FP
POP FP
RETN 0
STR8: DEFSTR "StarField"