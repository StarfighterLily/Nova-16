; NoBASIC compiler output
; Generated for Nova-16
ORG 0x0200
MOV P1, 0x7200
MOV P7:, 0xFF
MOV P0, 0x0124
MOV :P7, 0xFF
MOV SP, P7
MOV FP, SP
MOV [P0], P1
MOV P1, 0
MOV P0, 0x0120
MOV [P0], P1
INC P0
INC P0
MOV [P0], P1
MOV P6, 0x0120
MOV P5, [P6]
MOV P0, P6
INC P0
INC P0
MOV P4, [P0]
XOR P3, P3
MOV P2, 0
L1:
CMP P2, P4
JGE L2
MOV P1, P2
SHL P1, 1
ADD P1, P5
MOV [P1], P3
INC P2
JMP L1
L2:
; Free P3 (last use)
MOV P6, 0x0120
MOV R0, P4
MOV P5, [P6]
MOV P0, P6
INC P0
INC P0
MOV P4, [P0]
MOV P3, 5
MOV P7, 1
MOV P1, 0
MOV R1, 1
L3:
CMP P1, P4
JGE L4
CMP P7, 0
JGT L5
CMP P7, 0
JLT L6
JMP L4
L5:
CMP R1, P3
JGT L4
L6:
MOV P0, P1
SHL P0, 1
ADD P0, P5
MOV [P0], R1
INC P1
ADD R1, P7
JMP L3
L4:
MOV P6, 0x0120
MOV R0, P4
MOV P5, [P6]
MOV P0, P6
INC P0
INC P0
MOV P2, [P0]
MOV P1, 0
DEC P2
L7:
CMP P1, P2
JGE L8
MOV P0, P1
SHL P0, 1
ADD P0, P5
MOV P6, [P0]
MOV P3, P2
SHL P3, 1
ADD P3, P5
MOV P7, [P3]
MOV [P0], P7
MOV [P3], P6
INC P1
DEC P2
JMP L7
L8:
MOV VC, 15
MOV R0, P4
MOV VX, 0
TEXT STR8
ADD VY, 8
MOV P2, 1
MOV R0, 5
L10:
CMP P2, R0
JGT L11
PUSH P1
PUSH P2
PUSH P3
PUSH P4
PUSH P5
PUSH P6
MOV P1, 0x0120
CALL _nb_list_elem_addr
POP P6
POP P5
POP P4
POP P3
POP P2
POP P1
CMP P0, 0
JNZ L12
MOV R1, 0
JMP L13
L12:
PUSH P1
MOV P1, [P0]
MOV R1, :P1
POP P1
L13:
ITOS P1, R1
MOV VC, 15
MOV VX, 0
TEXT P1
ADD VY, 8
INC P2
JMP L10
L11:
L14:
KEYSTAT R0
CMP R0, 0
JZ L14
HLT
_nb_list_elem_addr:
; In:  P1=descriptor address, P2=1-based index
; Out: P0=element address (or 0 on invalid index/OOM)
PUSH P2
CMP P2, 1
JLT _nb_list_elem_addr_fail
MOV P3, [P1]
MOV P0, P1
INC P0
INC P0
MOV P4, [P0]
CMP P2, P4
JLE _nb_list_have_capacity
MOV P5, 0x0124
MOV P6, [P5]
MOV P0, P2
MOV P2, P4
CMP P2, 0
JGT _nb_list_cap_from_existing
MOV P2, 8
JMP _nb_list_cap_ready_base
_nb_list_cap_from_existing:
SHL P2, 1
_nb_list_cap_ready_base:
CMP P2, P0
JGE _nb_list_cap_ready
MOV P2, P0
_nb_list_cap_ready:
MOV P0, P2
SHL P0, 1
MOV P5, P6
ADD P5, P0
MOV P0, 0xEFFF
DEC P5
CMP P0, P5
JC _nb_list_elem_addr_fail
MOV P5, 0
_nb_list_zero_loop:
CMP P5, P2
JGE _nb_list_zero_done
MOV P0, P5
SHL P0, 1
ADD P0, P6
MOV [P0], 0
INC P5
JMP _nb_list_zero_loop
_nb_list_zero_done:
PUSH P1
CMP P4, 0
JLE _nb_list_copy_done
MOV P5, 0
_nb_list_copy_loop:
CMP P5, P4
JGE _nb_list_copy_done
MOV P0, P5
SHL P0, 1
ADD P0, P3
MOV P1, [P0]
MOV P0, P5
SHL P0, 1
ADD P0, P6
MOV [P0], P1
INC P5
JMP _nb_list_copy_loop
_nb_list_copy_done:
POP P1
MOV [P1], P6
MOV P0, P1
INC P0
INC P0
MOV [P0], P2
MOV P0, P2
SHL P0, 1
ADD P0, P6
MOV P5, 0x0124
MOV [P5], P0
MOV P4, P2
MOV P3, P6
_nb_list_have_capacity:
POP P2
MOV P0, P2
DEC P0
SHL P0, 1
ADD P0, P3
RET
_nb_list_elem_addr_fail:
POP P2
XOR P0, P0
RET
STR8: DEFSTR "Reversed list:"