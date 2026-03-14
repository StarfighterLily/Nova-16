; NoBASIC compiler output
; Generated for Nova-16
ORG 0x0200
MOV P7:, 0xFF
MOV :P7, 0xFF
MOV SP, P7
MOV FP, SP
; GLOBAL variable: programSize @ 0x0120
; GLOBAL variable: tapeSize @ 0x0122
; GLOBAL variable: pc @ 0x0124
; GLOBAL variable: ptr @ 0x0126
; GLOBAL variable: cmd @ 0x0128
; GLOBAL variable: cellValue @ 0x012A
; GLOBAL variable: handled @ 0x012C
; GLOBAL variable: outCount @ 0x012E
; GLOBAL variable: inputPos @ 0x0130
; GLOBAL variable: depth @ 0x0132
; GLOBAL variable: scan @ 0x0134
; GLOBAL variable: cell0 @ 0x0136
; GLOBAL variable: cell1 @ 0x0138
; GLOBAL variable: cell2 @ 0x013A
; GLOBAL variable: cell3 @ 0x013C
; GLOBAL variable: cell4 @ 0x013E
; GLOBAL variable: cell5 @ 0x0140
; GLOBAL variable: cell6 @ 0x0142
; GLOBAL variable: cell7 @ 0x0144
; GLOBAL variable: out0 @ 0x0146
; GLOBAL variable: out1 @ 0x0148
; GLOBAL variable: out2 @ 0x014A
; GLOBAL variable: out3 @ 0x014C
; GLOBAL variable: out4 @ 0x014E
; GLOBAL variable: out5 @ 0x0150
; GLOBAL variable: out6 @ 0x0152
; GLOBAL variable: out7 @ 0x0154
; GLOBAL variable: in0 @ 0x0156
; GLOBAL variable: in1 @ 0x0158
; GLOBAL variable: in2 @ 0x015A
; GLOBAL variable: in3 @ 0x015C
CALL _func_initializestate_0
CALL _func_runinterpreter_8
HLT

_func_initializestate_0:
; Function: initializestate
; Parameters: 
; Locals:  (0 bytes)
ENTER 0
MOV R1, 26
MOV P0, 0
MOV :P0, R1
MOV P1, 288
MOV [P1], P0
MOV R1, 1
SHL R1, 3
MOV P0, 0
MOV :P0, R1
MOV P1, 290
MOV [P1], P0
XOR R1, R1
MOV P0, 0
MOV :P0, R1
MOV P1, 292
MOV [P1], P0
XOR R1, R1
MOV P0, 0
MOV :P0, R1
MOV P1, 294
MOV [P1], P0
XOR R1, R1
MOV P0, 0
MOV :P0, R1
MOV P1, 296
MOV [P1], P0
XOR R1, R1
MOV P0, 0
MOV :P0, R1
MOV P1, 298
MOV [P1], P0
XOR R1, R1
MOV P0, 0
MOV :P0, R1
MOV P1, 300
MOV [P1], P0
XOR R1, R1
MOV P0, 0
MOV :P0, R1
MOV P1, 302
MOV [P1], P0
XOR R1, R1
MOV P0, 0
MOV :P0, R1
MOV P1, 304
MOV [P1], P0
XOR R1, R1
MOV P0, 0
MOV :P0, R1
MOV P1, 306
MOV [P1], P0
XOR R1, R1
MOV P0, 0
MOV :P0, R1
MOV P1, 308
MOV [P1], P0
XOR R1, R1
MOV P0, 0
MOV :P0, R1
MOV P1, 310
MOV [P1], P0
XOR R1, R1
MOV P0, 0
MOV :P0, R1
MOV P1, 312
MOV [P1], P0
XOR R1, R1
MOV P0, 0
MOV :P0, R1
MOV P1, 314
MOV [P1], P0
XOR R1, R1
MOV P0, 0
MOV :P0, R1
MOV P1, 316
MOV [P1], P0
XOR R1, R1
MOV P0, 0
MOV :P0, R1
MOV P1, 318
MOV [P1], P0
XOR R1, R1
MOV P0, 0
MOV :P0, R1
MOV P1, 320
MOV [P1], P0
XOR R1, R1
MOV P0, 0
MOV :P0, R1
MOV P1, 322
MOV [P1], P0
XOR R1, R1
MOV P0, 0
MOV :P0, R1
MOV P1, 324
MOV [P1], P0
XOR R1, R1
MOV P0, 0
MOV :P0, R1
MOV P1, 326
MOV [P1], P0
XOR R1, R1
MOV P0, 0
MOV :P0, R1
MOV P1, 328
MOV [P1], P0
XOR R1, R1
MOV P0, 0
MOV :P0, R1
MOV P1, 330
MOV [P1], P0
XOR R1, R1
MOV P0, 0
MOV :P0, R1
MOV P1, 332
MOV [P1], P0
XOR R1, R1
MOV P0, 0
MOV :P0, R1
MOV P1, 334
MOV [P1], P0
XOR R1, R1
MOV P0, 0
MOV :P0, R1
MOV P1, 336
MOV [P1], P0
XOR R1, R1
MOV P0, 0
MOV :P0, R1
MOV P1, 338
MOV [P1], P0
XOR R1, R1
MOV P0, 0
MOV :P0, R1
MOV P1, 340
MOV [P1], P0
XOR R1, R1
MOV P0, 0
MOV :P0, R1
MOV P1, 342
MOV [P1], P0
XOR R1, R1
MOV P0, 0
MOV :P0, R1
MOV P1, 344
MOV [P1], P0
XOR R1, R1
MOV P0, 0
MOV :P0, R1
MOV P1, 346
MOV [P1], P0
XOR R1, R1
MOV P0, 0
MOV :P0, R1
MOV P1, 348
MOV [P1], P0
MOV SP, FP
POP FP
RETN 0

_func_loadcommand_1:
; Function: loadcommand
; Parameters: 
; Locals:  (0 bytes)
ENTER 0
XOR R1, R1
MOV P0, 0
MOV :P0, R1
MOV P1, 296
MOV [P1], P0
MOV P0, 292
MOV P1, [P0]
XOR P2, P2
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L1
MOV R1, 43
MOV P0, 0
MOV :P0, R1
MOV P1, 296
MOV [P1], P0
L1:
MOV P0, 292
MOV P1, [P0]
MOV P2, 1
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L3
MOV R1, 43
MOV P0, 0
MOV :P0, R1
MOV P1, 296
MOV [P1], P0
L3:
MOV P0, 292
MOV P1, [P0]
MOV P2, 1
SHL P2, 1
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L5
MOV R1, 43
MOV P0, 0
MOV :P0, R1
MOV P1, 296
MOV [P1], P0
L5:
MOV P0, 292
MOV P1, [P0]
MOV P2, 3
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L7
MOV R1, 43
MOV P0, 0
MOV :P0, R1
MOV P1, 296
MOV [P1], P0
L7:
MOV P0, 292
MOV P1, [P0]
MOV P2, 1
SHL P2, 2
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L9
MOV R1, 43
MOV P0, 0
MOV :P0, R1
MOV P1, 296
MOV [P1], P0
L9:
MOV P0, 292
MOV P1, [P0]
MOV P2, 5
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L11
MOV R1, 43
MOV P0, 0
MOV :P0, R1
MOV P1, 296
MOV [P1], P0
L11:
MOV P0, 292
MOV P1, [P0]
MOV P2, 6
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L13
MOV R1, 43
MOV P0, 0
MOV :P0, R1
MOV P1, 296
MOV [P1], P0
L13:
MOV P0, 292
MOV P1, [P0]
MOV P2, 7
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L15
MOV R1, 43
MOV P0, 0
MOV :P0, R1
MOV P1, 296
MOV [P1], P0
L15:
MOV P0, 292
MOV P1, [P0]
MOV P2, 1
SHL P2, 3
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L17
MOV R1, 91
MOV P0, 0
MOV :P0, R1
MOV P1, 296
MOV [P1], P0
L17:
MOV P0, 292
MOV P1, [P0]
MOV P2, 9
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L19
MOV R1, 62
MOV P0, 0
MOV :P0, R1
MOV P1, 296
MOV [P1], P0
L19:
MOV P0, 292
MOV P1, [P0]
MOV P2, 10
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L21
MOV R1, 43
MOV P0, 0
MOV :P0, R1
MOV P1, 296
MOV [P1], P0
L21:
MOV P0, 292
MOV P1, [P0]
MOV P2, 11
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L23
MOV R1, 43
MOV P0, 0
MOV :P0, R1
MOV P1, 296
MOV [P1], P0
L23:
MOV P0, 292
MOV P1, [P0]
MOV P2, 12
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L25
MOV R1, 43
MOV P0, 0
MOV :P0, R1
MOV P1, 296
MOV [P1], P0
L25:
MOV P0, 292
MOV P1, [P0]
MOV P2, 13
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L27
MOV R1, 43
MOV P0, 0
MOV :P0, R1
MOV P1, 296
MOV [P1], P0
L27:
MOV P0, 292
MOV P1, [P0]
MOV P2, 14
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L29
MOV R1, 43
MOV P0, 0
MOV :P0, R1
MOV P1, 296
MOV [P1], P0
L29:
MOV P0, 292
MOV P1, [P0]
MOV P2, 15
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L31
MOV R1, 43
MOV P0, 0
MOV :P0, R1
MOV P1, 296
MOV [P1], P0
L31:
MOV P0, 292
MOV P1, [P0]
MOV P2, 1
SHL P2, 4
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L33
MOV R1, 43
MOV P0, 0
MOV :P0, R1
MOV P1, 296
MOV [P1], P0
L33:
MOV P0, 292
MOV P1, [P0]
MOV P2, 17
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L35
MOV R1, 43
MOV P0, 0
MOV :P0, R1
MOV P1, 296
MOV [P1], P0
L35:
MOV P0, 292
MOV P1, [P0]
MOV P2, 18
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L37
MOV R1, 60
MOV P0, 0
MOV :P0, R1
MOV P1, 296
MOV [P1], P0
L37:
MOV P0, 292
MOV P1, [P0]
MOV P2, 19
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L39
MOV R1, 45
MOV P0, 0
MOV :P0, R1
MOV P1, 296
MOV [P1], P0
L39:
MOV P0, 292
MOV P1, [P0]
MOV P2, 20
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L41
MOV R1, 93
MOV P0, 0
MOV :P0, R1
MOV P1, 296
MOV [P1], P0
L41:
MOV P0, 292
MOV P1, [P0]
MOV P2, 21
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L43
MOV R1, 62
MOV P0, 0
MOV :P0, R1
MOV P1, 296
MOV [P1], P0
L43:
MOV P0, 292
MOV P1, [P0]
MOV P2, 22
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L45
MOV R1, 43
MOV P0, 0
MOV :P0, R1
MOV P1, 296
MOV [P1], P0
L45:
MOV P0, 292
MOV P1, [P0]
MOV P2, 23
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L47
MOV R1, 46
MOV P0, 0
MOV :P0, R1
MOV P1, 296
MOV [P1], P0
L47:
MOV P0, 292
MOV P1, [P0]
MOV P2, 24
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L49
MOV R1, 43
MOV P0, 0
MOV :P0, R1
MOV P1, 296
MOV [P1], P0
L49:
MOV P0, 292
MOV P1, [P0]
MOV P2, 25
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L51
MOV R1, 46
MOV P0, 0
MOV :P0, R1
MOV P1, 296
MOV [P1], P0
L51:
MOV SP, FP
POP FP
RETN 0

_func_readcell_2:
; Function: readcell
; Parameters: 
; Locals:  (0 bytes)
ENTER 0
XOR R1, R1
MOV P0, 0
MOV :P0, R1
MOV P1, 298
MOV [P1], P0
MOV P0, 294
MOV P1, [P0]
XOR P2, P2
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L53
MOV P0, 310
MOV P0, [P0]
MOV P1, 298
MOV [P1], P0
L53:
MOV P0, 294
MOV P1, [P0]
MOV P2, 1
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L55
MOV P0, 312
MOV P0, [P0]
MOV P1, 298
MOV [P1], P0
L55:
MOV P0, 294
MOV P1, [P0]
MOV P2, 1
SHL P2, 1
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L57
MOV P0, 314
MOV P0, [P0]
MOV P1, 298
MOV [P1], P0
L57:
MOV P0, 294
MOV P1, [P0]
MOV P2, 3
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L59
MOV P0, 316
MOV P0, [P0]
MOV P1, 298
MOV [P1], P0
L59:
MOV P0, 294
MOV P1, [P0]
MOV P2, 1
SHL P2, 2
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L61
MOV P0, 318
MOV P0, [P0]
MOV P1, 298
MOV [P1], P0
L61:
MOV P0, 294
MOV P1, [P0]
MOV P2, 5
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L63
MOV P0, 320
MOV P0, [P0]
MOV P1, 298
MOV [P1], P0
L63:
MOV P0, 294
MOV P1, [P0]
MOV P2, 6
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L65
MOV P0, 322
MOV P0, [P0]
MOV P1, 298
MOV [P1], P0
L65:
MOV P0, 294
MOV P1, [P0]
MOV P2, 7
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L67
MOV P0, 324
MOV P0, [P0]
MOV P1, 298
MOV [P1], P0
L67:
MOV SP, FP
POP FP
RETN 0

_func_writecell_3:
; Function: writecell
; Parameters: 
; Locals:  (0 bytes)
ENTER 0
MOV P0, 294
MOV P1, [P0]
XOR P2, P2
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L69
MOV P0, 298
MOV P0, [P0]
MOV P1, 310
MOV [P1], P0
L69:
MOV P0, 294
MOV P1, [P0]
MOV P2, 1
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L71
MOV P0, 298
MOV P0, [P0]
MOV P1, 312
MOV [P1], P0
L71:
MOV P0, 294
MOV P1, [P0]
MOV P2, 1
SHL P2, 1
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L73
MOV P0, 298
MOV P0, [P0]
MOV P1, 314
MOV [P1], P0
L73:
MOV P0, 294
MOV P1, [P0]
MOV P2, 3
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L75
MOV P0, 298
MOV P0, [P0]
MOV P1, 316
MOV [P1], P0
L75:
MOV P0, 294
MOV P1, [P0]
MOV P2, 1
SHL P2, 2
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L77
MOV P0, 298
MOV P0, [P0]
MOV P1, 318
MOV [P1], P0
L77:
MOV P0, 294
MOV P1, [P0]
MOV P2, 5
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L79
MOV P0, 298
MOV P0, [P0]
MOV P1, 320
MOV [P1], P0
L79:
MOV P0, 294
MOV P1, [P0]
MOV P2, 6
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L81
MOV P0, 298
MOV P0, [P0]
MOV P1, 322
MOV [P1], P0
L81:
MOV P0, 294
MOV P1, [P0]
MOV P2, 7
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L83
MOV P0, 298
MOV P0, [P0]
MOV P1, 324
MOV [P1], P0
L83:
MOV SP, FP
POP FP
RETN 0

_func_emitbyte_4:
; Function: emitbyte
; Parameters: 
; Locals:  (0 bytes)
ENTER 0
MOV P0, 302
MOV P1, [P0]
XOR P2, P2
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L85
MOV P0, 298
MOV P0, [P0]
MOV P1, 326
MOV [P1], P0
L85:
MOV P0, 302
MOV P1, [P0]
MOV P2, 1
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L87
MOV P0, 298
MOV P0, [P0]
MOV P1, 328
MOV [P1], P0
L87:
MOV P0, 302
MOV P1, [P0]
MOV P2, 1
SHL P2, 1
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L89
MOV P0, 298
MOV P0, [P0]
MOV P1, 330
MOV [P1], P0
L89:
MOV P0, 302
MOV P1, [P0]
MOV P2, 3
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L91
MOV P0, 298
MOV P0, [P0]
MOV P1, 332
MOV [P1], P0
L91:
MOV P0, 302
MOV P1, [P0]
MOV P2, 1
SHL P2, 2
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L93
MOV P0, 298
MOV P0, [P0]
MOV P1, 334
MOV [P1], P0
L93:
MOV P0, 302
MOV P1, [P0]
MOV P2, 5
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L95
MOV P0, 298
MOV P0, [P0]
MOV P1, 336
MOV [P1], P0
L95:
MOV P0, 302
MOV P1, [P0]
MOV P2, 6
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L97
MOV P0, 298
MOV P0, [P0]
MOV P1, 338
MOV [P1], P0
L97:
MOV P0, 302
MOV P1, [P0]
MOV P2, 7
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L99
MOV P0, 298
MOV P0, [P0]
MOV P1, 340
MOV [P1], P0
L99:
MOV P0, 302
MOV P1, [P0]
MOV P2, 1
SHL P2, 3
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JGE L101
MOV P0, 302
MOV P0, [P0]
; Preserve left operand in register across right-side evaluation
MOV R2, P0
MOV R3, 1
MOV R1, R2
ADD R1, R3
; Free R3 (last use)
MOV P0, 0
MOV :P0, R1
MOV P1, 302
MOV [P1], P0
L101:
MOV SP, FP
POP FP
RETN 0

_func_readinputvalue_5:
; Function: readinputvalue
; Parameters: 
; Locals:  (0 bytes)
ENTER 0
XOR R1, R1
MOV P0, 0
MOV :P0, R1
MOV P1, 298
MOV [P1], P0
MOV P0, 304
MOV P1, [P0]
XOR P2, P2
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L103
MOV P0, 342
MOV P0, [P0]
MOV P1, 298
MOV [P1], P0
L103:
MOV P0, 304
MOV P1, [P0]
MOV P2, 1
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L105
MOV P0, 344
MOV P0, [P0]
MOV P1, 298
MOV [P1], P0
L105:
MOV P0, 304
MOV P1, [P0]
MOV P2, 1
SHL P2, 1
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L107
MOV P0, 346
MOV P0, [P0]
MOV P1, 298
MOV [P1], P0
L107:
MOV P0, 304
MOV P1, [P0]
MOV P2, 3
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L109
MOV P0, 348
MOV P0, [P0]
MOV P1, 298
MOV [P1], P0
L109:
MOV P0, 298
MOV P1, [P0]
XOR P2, P2
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JZ L111
MOV P0, 304
MOV P0, [P0]
; Preserve left operand in register across right-side evaluation
MOV R2, P0
MOV R3, 1
MOV R1, R2
ADD R1, R3
; Free R3 (last use)
MOV P0, 0
MOV :P0, R1
MOV P1, 304
MOV [P1], P0
L111:
MOV SP, FP
POP FP
RETN 0

_func_skipforward_6:
; Function: skipforward
; Parameters: 
; Locals:  (0 bytes)
ENTER 0
MOV R1, 1
MOV P0, 0
MOV :P0, R1
MOV P1, 306
MOV [P1], P0
MOV P0, 292
MOV P0, [P0]
; Preserve left operand in register across right-side evaluation
MOV R2, P0
MOV R3, 1
MOV R1, R2
ADD R1, R3
; Free R3 (last use)
MOV P0, 0
MOV :P0, R1
MOV P1, 308
MOV [P1], P0
L113:
MOV P0, 306
MOV P1, [P0]
XOR P2, P2
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JLE L114
MOV P0, 308
MOV P0, [P0]
MOV P1, 292
MOV [P1], P0
CALL _func_loadcommand_1
MOV P0, 296
MOV P1, [P0]
MOV P2, 91
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L115
MOV P0, 306
MOV P0, [P0]
; Preserve left operand in register across right-side evaluation
MOV R2, P0
MOV R3, 1
MOV R1, R2
ADD R1, R3
; Free R3 (last use)
MOV P0, 0
MOV :P0, R1
MOV P1, 306
MOV [P1], P0
L115:
MOV P0, 296
MOV P1, [P0]
MOV P2, 93
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L117
MOV P0, 306
MOV P0, [P0]
; Preserve left operand in register across right-side evaluation
MOV R2, P0
MOV R3, 1
MOV R1, R2
SUB R1, R3
; Free R3 (last use)
MOV P0, 0
MOV :P0, R1
MOV P1, 306
MOV [P1], P0
L117:
MOV P0, 308
MOV P0, [P0]
; Preserve left operand in register across right-side evaluation
MOV R2, P0
MOV R3, 1
MOV R1, R2
ADD R1, R3
; Free R3 (last use)
MOV P0, 0
MOV :P0, R1
MOV P1, 308
MOV [P1], P0
JMP L113
L114:
MOV P0, 308
MOV P0, [P0]
MOV P1, 292
MOV [P1], P0
MOV SP, FP
POP FP
RETN 0

_func_skipbackward_7:
; Function: skipbackward
; Parameters: 
; Locals:  (0 bytes)
ENTER 0
MOV R1, 1
MOV P0, 0
MOV :P0, R1
MOV P1, 306
MOV [P1], P0
MOV P0, 292
MOV P0, [P0]
; Preserve left operand in register across right-side evaluation
MOV R2, P0
MOV R3, 1
MOV R1, R2
SUB R1, R3
; Free R3 (last use)
MOV P0, 0
MOV :P0, R1
MOV P1, 308
MOV [P1], P0
L119:
MOV P0, 306
MOV P1, [P0]
XOR P2, P2
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JLE L120
MOV P0, 308
MOV P0, [P0]
MOV P1, 292
MOV [P1], P0
CALL _func_loadcommand_1
MOV P0, 296
MOV P1, [P0]
MOV P2, 93
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L121
MOV P0, 306
MOV P0, [P0]
; Preserve left operand in register across right-side evaluation
MOV R2, P0
MOV R3, 1
MOV R1, R2
ADD R1, R3
; Free R3 (last use)
MOV P0, 0
MOV :P0, R1
MOV P1, 306
MOV [P1], P0
L121:
MOV P0, 296
MOV P1, [P0]
MOV P2, 91
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L123
MOV P0, 306
MOV P0, [P0]
; Preserve left operand in register across right-side evaluation
MOV R2, P0
MOV R3, 1
MOV R1, R2
SUB R1, R3
; Free R3 (last use)
MOV P0, 0
MOV :P0, R1
MOV P1, 306
MOV [P1], P0
L123:
MOV P0, 306
MOV P1, [P0]
XOR P2, P2
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JLE L125
MOV P0, 308
MOV P0, [P0]
; Preserve left operand in register across right-side evaluation
MOV R2, P0
MOV R3, 1
MOV R1, R2
SUB R1, R3
; Free R3 (last use)
MOV P0, 0
MOV :P0, R1
MOV P1, 308
MOV [P1], P0
L125:
JMP L119
L120:
MOV P0, 308
MOV P0, [P0]
; Preserve left operand in register across right-side evaluation
MOV R2, P0
MOV R3, 1
MOV R1, R2
ADD R1, R3
; Free R3 (last use)
MOV P0, 0
MOV :P0, R1
MOV P1, 292
MOV [P1], P0
MOV SP, FP
POP FP
RETN 0

_func_runinterpreter_8:
; Function: runinterpreter
; Parameters: 
; Locals:  (0 bytes)
ENTER 0
XOR R1, R1
MOV P0, 0
MOV :P0, R1
MOV P1, 292
MOV [P1], P0
XOR R1, R1
MOV P0, 0
MOV :P0, R1
MOV P1, 294
MOV [P1], P0
XOR R1, R1
MOV P0, 0
MOV :P0, R1
MOV P1, 302
MOV [P1], P0
XOR R1, R1
MOV P0, 0
MOV :P0, R1
MOV P1, 304
MOV [P1], P0
L127:
MOV P0, 292
MOV P1, [P0]
MOV P0, 288
MOV P2, [P0]
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JGE L128
CALL _func_loadcommand_1
XOR R1, R1
MOV P0, 0
MOV :P0, R1
MOV P1, 300
MOV [P1], P0
MOV P0, 296
MOV P1, [P0]
MOV P2, 62
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L129
MOV P0, 294
MOV P0, [P0]
; Preserve left operand in register across right-side evaluation
MOV R2, P0
MOV R3, 1
MOV R1, R2
ADD R1, R3
; Free R3 (last use)
MOV P0, 0
MOV :P0, R1
MOV P1, 294
MOV [P1], P0
MOV P0, 294
MOV P1, [P0]
MOV P0, 290
MOV P2, [P0]
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JLT L131
XOR R1, R1
MOV P0, 0
MOV :P0, R1
MOV P1, 294
MOV [P1], P0
L131:
MOV P0, 292
MOV P0, [P0]
; Preserve left operand in register across right-side evaluation
MOV R2, P0
MOV R3, 1
MOV R1, R2
ADD R1, R3
; Free R3 (last use)
MOV P0, 0
MOV :P0, R1
MOV P1, 292
MOV [P1], P0
MOV R1, 1
MOV P0, 0
MOV :P0, R1
MOV P1, 300
MOV [P1], P0
L129:
MOV P0, 296
MOV P1, [P0]
MOV P2, 60
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L133
MOV P0, 294
MOV P1, [P0]
XOR P2, P2
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L135
MOV P0, 290
MOV P0, [P0]
; Preserve left operand in register across right-side evaluation
MOV R2, P0
MOV R3, 1
MOV R1, R2
SUB R1, R3
; Free R3 (last use)
MOV P0, 0
MOV :P0, R1
MOV P1, 294
MOV [P1], P0
JMP L136
L135:
MOV P0, 294
MOV P0, [P0]
; Preserve left operand in register across right-side evaluation
MOV R2, P0
MOV R3, 1
MOV R1, R2
SUB R1, R3
; Free R3 (last use)
MOV P0, 0
MOV :P0, R1
MOV P1, 294
MOV [P1], P0
L136:
MOV P0, 292
MOV P0, [P0]
; Preserve left operand in register across right-side evaluation
MOV R2, P0
MOV R3, 1
MOV R1, R2
ADD R1, R3
; Free R3 (last use)
MOV P0, 0
MOV :P0, R1
MOV P1, 292
MOV [P1], P0
MOV R1, 1
MOV P0, 0
MOV :P0, R1
MOV P1, 300
MOV [P1], P0
L133:
MOV P0, 296
MOV P1, [P0]
MOV P2, 43
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L137
CALL _func_readcell_2
MOV P0, 298
MOV P1, [P0]
MOV P2, 255
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L139
XOR R1, R1
MOV P0, 0
MOV :P0, R1
MOV P1, 298
MOV [P1], P0
JMP L140
L139:
MOV P0, 298
MOV P0, [P0]
; Preserve left operand in register across right-side evaluation
MOV R2, P0
MOV R3, 1
MOV R1, R2
ADD R1, R3
; Free R3 (last use)
MOV P0, 0
MOV :P0, R1
MOV P1, 298
MOV [P1], P0
L140:
CALL _func_writecell_3
MOV P0, 292
MOV P0, [P0]
; Preserve left operand in register across right-side evaluation
MOV R2, P0
MOV R3, 1
MOV R1, R2
ADD R1, R3
; Free R3 (last use)
MOV P0, 0
MOV :P0, R1
MOV P1, 292
MOV [P1], P0
MOV R1, 1
MOV P0, 0
MOV :P0, R1
MOV P1, 300
MOV [P1], P0
L137:
MOV P0, 296
MOV P1, [P0]
MOV P2, 45
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L141
CALL _func_readcell_2
MOV P0, 298
MOV P1, [P0]
XOR P2, P2
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L143
MOV R1, 255
MOV P0, 0
MOV :P0, R1
MOV P1, 298
MOV [P1], P0
JMP L144
L143:
MOV P0, 298
MOV P0, [P0]
; Preserve left operand in register across right-side evaluation
MOV R2, P0
MOV R3, 1
MOV R1, R2
SUB R1, R3
; Free R3 (last use)
MOV P0, 0
MOV :P0, R1
MOV P1, 298
MOV [P1], P0
L144:
CALL _func_writecell_3
MOV P0, 292
MOV P0, [P0]
; Preserve left operand in register across right-side evaluation
MOV R2, P0
MOV R3, 1
MOV R1, R2
ADD R1, R3
; Free R3 (last use)
MOV P0, 0
MOV :P0, R1
MOV P1, 292
MOV [P1], P0
MOV R1, 1
MOV P0, 0
MOV :P0, R1
MOV P1, 300
MOV [P1], P0
L141:
MOV P0, 296
MOV P1, [P0]
MOV P2, 46
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L145
CALL _func_readcell_2
CALL _func_emitbyte_4
MOV P0, 292
MOV P0, [P0]
; Preserve left operand in register across right-side evaluation
MOV R2, P0
MOV R3, 1
MOV R1, R2
ADD R1, R3
; Free R3 (last use)
MOV P0, 0
MOV :P0, R1
MOV P1, 292
MOV [P1], P0
MOV R1, 1
MOV P0, 0
MOV :P0, R1
MOV P1, 300
MOV [P1], P0
L145:
MOV P0, 296
MOV P1, [P0]
MOV P2, 44
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L147
CALL _func_readinputvalue_5
CALL _func_writecell_3
MOV P0, 292
MOV P0, [P0]
; Preserve left operand in register across right-side evaluation
MOV R2, P0
MOV R3, 1
MOV R1, R2
ADD R1, R3
; Free R3 (last use)
MOV P0, 0
MOV :P0, R1
MOV P1, 292
MOV [P1], P0
MOV R1, 1
MOV P0, 0
MOV :P0, R1
MOV P1, 300
MOV [P1], P0
L147:
MOV P0, 296
MOV P1, [P0]
MOV P2, 91
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L149
CALL _func_readcell_2
MOV P0, 298
MOV P1, [P0]
XOR P2, P2
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L151
CALL _func_skipforward_6
JMP L152
L151:
MOV P0, 292
MOV P0, [P0]
; Preserve left operand in register across right-side evaluation
MOV R2, P0
MOV R3, 1
MOV R1, R2
ADD R1, R3
; Free R3 (last use)
MOV P0, 0
MOV :P0, R1
MOV P1, 292
MOV [P1], P0
L152:
MOV R1, 1
MOV P0, 0
MOV :P0, R1
MOV P1, 300
MOV [P1], P0
L149:
MOV P0, 296
MOV P1, [P0]
MOV P2, 93
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L153
CALL _func_readcell_2
MOV P0, 298
MOV P1, [P0]
XOR P2, P2
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JZ L155
CALL _func_skipbackward_7
JMP L156
L155:
MOV P0, 292
MOV P0, [P0]
; Preserve left operand in register across right-side evaluation
MOV R2, P0
MOV R3, 1
MOV R1, R2
ADD R1, R3
; Free R3 (last use)
MOV P0, 0
MOV :P0, R1
MOV P1, 292
MOV [P1], P0
L156:
MOV R1, 1
MOV P0, 0
MOV :P0, R1
MOV P1, 300
MOV [P1], P0
L153:
MOV P0, 300
MOV P1, [P0]
XOR P2, P2
CMP P1, P2
; Free P1 (last use)
; Free P2 (last use)
JNZ L157
MOV P0, 292
MOV P0, [P0]
; Preserve left operand in register across right-side evaluation
MOV R2, P0
MOV R3, 1
MOV R1, R2
ADD R1, R3
; Free R3 (last use)
MOV P0, 0
MOV :P0, R1
MOV P1, 292
MOV [P1], P0
L157:
JMP L127
L128:
MOV SP, FP
POP FP
RETN 0