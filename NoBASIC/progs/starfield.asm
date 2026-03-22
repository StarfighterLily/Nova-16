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
MOV P0, 288
MOV P1, R1
MOV [P0], P1
XOR R1, R1
; Store to stext.toggle
MOV P0, 290
MOV P1, R1
MOV [P0], P1
MOV VM, 0
MOV VL, 1
XOR R1, R1
MOV P3, R1
MOV R0, 150
L14:
CMP P3, R0
JGT L15
XOR R0, R0
MOV P2, R0
MOV P5, 150
L16:
CMP P2, P5
JGT L17
RND R1
; Preserve left operand in register across right-side evaluation
MOV R2, R1
MOV R0, R2
ADD R0, P3
MOV VX, R0
RND R2
; Preserve left operand in register across right-side evaluation
MOV R4, R2
MOV R0, R4
SUB R0, P2
MOV VY, R0
MOV R4, 1
MOV R6, 1
SHL R6, 2
RNDR R0, R4, R6
; Free R4 (last use)
; Free R6 (last use)
MOV VC, R0
SWRITE VC
INC P2
JMP L16
L17:
INC P3
JMP L14
L15:
MOV R0, 1
XOR R1, R1
SROT R0, R1
; Free R0 (last use)
; Free R1 (last use)
MOV VM, 0
MOV VL, 1
SHL VL, 1
XOR R1, R1
MOV P3, R1
MOV R0, 50
L18:
CMP P3, R0
JGT L19
XOR R0, R0
MOV P2, R0
MOV P5, 50
L20:
CMP P2, P5
JGT L21
RND R1
; Preserve left operand in register across right-side evaluation
MOV R2, R1
MOV R0, R2
ADD R0, P3
MOV VX, R0
RND R2
; Preserve left operand in register across right-side evaluation
MOV R4, R2
MOV R0, R4
ADD R0, P3
MOV VY, R0
MOV R4, 5
MOV R6, 9
RNDR R0, R4, R6
; Free R4 (last use)
; Free R6 (last use)
MOV VC, R0
SWRITE VC
INC P2
JMP L20
L21:
INC P3
JMP L18
L19:
MOV R0, 1
MOV R1, 1
SROT R0, R1
; Free R0 (last use)
; Free R1 (last use)
MOV VM, 0
MOV VL, 3
XOR R1, R1
MOV P3, R1
MOV R0, 10
L22:
CMP P3, R0
JGT L23
XOR R0, R0
MOV P2, R0
MOV P5, 5
L24:
CMP P2, P5
JGT L25
RND R1
; Preserve left operand in register across right-side evaluation
MOV R2, R1
MOV R0, R2
SUB R0, P3
MOV VX, R0
RND R2
; Preserve left operand in register across right-side evaluation
MOV R4, R2
MOV R0, R4
SUB R0, P2
MOV VY, R0
MOV R4, 10
MOV R6, 15
RNDR R0, R4, R6
; Free R4 (last use)
; Free R6 (last use)
MOV VC, R0
SWRITE VC
INC P2
JMP L24
L25:
INC P3
JMP L22
L23:
MOV R0, 1
MOV R1, 1
SHL R1, 1
SROT R0, R1
; Free R0 (last use)
; Free R1 (last use)
L26:
MOV R1, 1
WHILE R1
JZ L27
PUSH P2
PUSH P3
CALL _func_scrollbg_0
POP P3
POP P2
XOR R1, R1
MOV P3, R1
MOV R0, 255
L28:
CMP P3, R0
JGT L29
PUSH P2
PUSH P3
CALL _func_flashtext_1
POP P3
POP P2
INC P3
JMP L28
L29:
XOR R1, R1
MOV P3, R1
MOV R0, 255
L30:
CMP P3, R0
JGT L31
XOR R0, R0
MOV P2, R0
MOV P5, 255
L32:
CMP P2, P5
JGT L33
INC P2
JMP L32
L33:
INC P3
JMP L30
L31:
JMP L26
L27:
HLT
_func_scrollbg_0:
; Function: scrollbg
; Parameters:
; Locals:  (0 bytes)
ENTER 0
MOV VM, 0
MOV VL, 1
XOR R0, R0
MOV R1, 1
SROL R0, R1
; Free R0 (last use)
; Free R1 (last use)
MOV VM, 0
MOV VL, 1
SHL VL, 1
XOR R0, R0
MOV R1, 1
SHL R1, 1
SROL R0, R1
; Free R0 (last use)
; Free R1 (last use)
MOV VM, 0
MOV VL, 3
XOR R0, R0
MOV R1, 3
SROL R0, R1
; Free R0 (last use)
; Free R1 (last use)
XOR R0, R0
MOV P1, R0
MOV P2, 255
L1:
CMP P1, P2
JGT L2
INC P1
JMP L1
L2:
MOV SP, FP
POP FP
RETN 0
_func_flashtext_1:
; Function: flashtext
; Parameters:
; Locals:  (0 bytes)
ENTER 0
MOV VM, 0
MOV VL, 1
SHL VL, 2
; Allocate struct stext (stext) at 0x0120
; Load stext.toggle
MOV P0, 290
MOV P1, [P0]
XOR P2, P2
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L3
; Load stext.color
MOV P0, 288
MOV P1, [P0]
MOV R0, P1
ADD P1, 1
; Store to stext.color
MOV P0, 288
MOV [P0], P1
; Load stext.color
MOV P0, 288
MOV P1, [P0]
MOV P2, 31
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JLE L5
MOV R1, 31
; Store to stext.color
MOV P0, 288
MOV P1, R1
MOV [P0], P1
MOV R1, 1
; Store to stext.toggle
MOV P0, 290
MOV P1, R1
MOV [P0], P1
L5:
L3:
; Load stext.toggle
MOV P0, 290
MOV P1, [P0]
MOV P2, 1
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L7
; Load stext.color
MOV P0, 288
MOV P1, [P0]
MOV R0, P1
SUB P1, 1
; Store to stext.color
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
JGE L9
MOV R1, 1
SHL R1, 4
; Store to stext.color
MOV P0, 288
MOV P1, R1
MOV [P0], P1
XOR R1, R1
; Store to stext.toggle
MOV P0, 290
MOV P1, R1
MOV [P0], P1
L9:
L7:
MOV VX, 80
MOV VY, 120
; Load stext.color
MOV P0, 288
MOV P1, [P0]
MOV VC, P1
TEXT STR10
XOR R0, R0
MOV P1, R0
MOV P2, 255
L12:
CMP P1, P2
JGT L13
INC P1
JMP L12
L13:
MOV SP, FP
POP FP
RETN 0
STR10: DEFSTR "StarField"